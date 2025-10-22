"""
Worker de RabbitMQ (Procesamiento Asíncrono)
===========================================

Qué es este archivo:
- Un proceso separado del API que se conecta a RabbitMQ, consume mensajes de la cola
  `notifications.queue` y ejecuta el envío real de la notificación usando el canal
  correspondiente (Email, SMS, WhatsApp, Push).

Por qué existe (idea principal):
- El API sólo encola el trabajo rápido (no envía). El worker procesa en segundo plano
  para que el API sea rápido y tolerante a picos de tráfico.

Conceptos clave en palabras sencillas:
- Exchange: "punto de distribución" donde publicamos mensajes.
- Queue (cola): "buzón" desde el que el worker lee mensajes.
- Routing key: etiqueta que ayuda a decidir a qué cola va el mensaje.
- DLQ (Dead Letter Queue): cola donde enviamos mensajes que fallaron demasiadas veces
  para que no se pierdan y podamos revisarlos.
- Retries (reintentos): si algo falla (por ejemplo, proveedor caído), volvemos a
  intentar tras una espera (backoff). Aquí usamos 3 esperas crecientes.

Cómo probarlo en local (resumen):
1) Levanta RabbitMQ, app y worker con docker-compose.
2) Llama al endpoint POST /notify del API con un JSON que incluya `channel`,
   `destination`, `message` y opcionalmente `subject`.
3) Observa logs del contenedor `notifications-worker` para ver el procesamiento.

Variables importantes (lee tu .env):
- WORKER_MAX_RETRIES: número máximo de reintentos.
- WORKER_RETRY_DELAY_1/2/3: segundos de espera antes del 1er/2do/3er reintento.
- DEFAULT_CHANNEL: canal por defecto si el payload no trae `channel`.
"""

import os
import json
import asyncio
import logging
from typing import Any, Dict, Optional
from datetime import datetime

import aio_pika
from app.channels.factory import create_channel
from app.models import NotificationChannel, Notification, NotificationStatus
from app.db import SessionLocal

logger = logging.getLogger(__name__)
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))

RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "localhost")
RABBITMQ_PORT = int(os.getenv("RABBITMQ_PORT", "5672"))
RABBITMQ_USERNAME = os.getenv("RABBITMQ_USERNAME", "admin")
RABBITMQ_PASSWORD = os.getenv("RABBITMQ_PASSWORD", "admin")
RABBITMQ_VHOST = os.getenv("RABBITMQ_VHOST", "foro")

EXCHANGE_NAME = os.getenv("AMQP_EXCHANGE", "notifications.exchange")
EXCHANGE_TYPE = os.getenv("AMQP_EXCHANGE_TYPE", "direct").lower()
QUEUE_NAME = os.getenv("AMQP_QUEUE", "notifications.queue")
ROUTING_KEY = os.getenv("AMQP_ROUTING_KEY", "notifications.key")
DECLARE_INFRA = os.getenv("WORKER_DECLARE_INFRA", "true").lower() == "true"
DLX_NAME = os.getenv("AMQP_DLX_NAME", f"{EXCHANGE_NAME}.dlx")
DLX_TYPE = os.getenv("AMQP_DLX_TYPE", "fanout").lower()

# Retries
MAX_RETRIES = int(os.getenv("WORKER_MAX_RETRIES", "3"))
RETRY_DELAYS = [
    int(os.getenv("WORKER_RETRY_DELAY_1", "5")),    # seconds
    int(os.getenv("WORKER_RETRY_DELAY_2", "30")),
    int(os.getenv("WORKER_RETRY_DELAY_3", "120")),
]

# Default channel if payload doesn’t include it
DEFAULT_CHANNEL = os.getenv("DEFAULT_CHANNEL", "email").lower()

def _parse_channel(channel_value: Optional[str]) -> NotificationChannel:
    value = (channel_value or DEFAULT_CHANNEL).lower()
    mapping = {
        "email": NotificationChannel.EMAIL,
        "sms": NotificationChannel.SMS,
        "whatsapp": NotificationChannel.WHATSAPP,
        "push": NotificationChannel.PUSH,
    }
    if value not in mapping:
        raise ValueError(f"Canal no soportado: {value}")
    return mapping[value]

def _save_notification_to_db(
    user_id: str,
    channel: NotificationChannel,
    destination: str,
    message: str,
    subject: Optional[str] = None,
    status: NotificationStatus = NotificationStatus.PENDING
) -> Optional[int]:
    """Guarda una notificación en la base de datos"""
    # Usar la variable de entorno DB_URL del worker
    from app.db import create_engine, sessionmaker
    from sqlalchemy.orm import Session
    
    db_url = os.getenv("DB_URL", "postgresql+psycopg2://notifications:notifications@postgres-notifications:5432/notifications")
    engine = create_engine(db_url, pool_pre_ping=True)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    db = SessionLocal()
    try:
        notification = Notification(
            user_id=user_id,
            channel=channel,
            destination=destination,
            subject=subject,
            message=message,
            status=status,
            created_at=datetime.utcnow()
        )
        db.add(notification)
        db.commit()
        db.refresh(notification)
        return notification.id
    except Exception as e:
        logger.error(f"Error guardando notificación en BD: {e}")
        db.rollback()
        return None
    finally:
        db.close()

def _update_notification_status(
    notification_id: int,
    status: NotificationStatus,
    error_message: Optional[str] = None,
    cost: Optional[str] = None
) -> bool:
    """Actualiza el estado de una notificación en la base de datos"""
    # Usar la variable de entorno DB_URL del worker
    from app.db import create_engine, sessionmaker
    
    db_url = os.getenv("DB_URL", "postgresql+psycopg2://notifications:notifications@postgres-notifications:5432/notifications")
    engine = create_engine(db_url, pool_pre_ping=True)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    db = SessionLocal()
    try:
        notification = db.get(Notification, notification_id)
        if notification:
            notification.status = status
            if status == NotificationStatus.SENT:
                notification.sent_at = datetime.utcnow()
            if error_message:
                notification.error_message = error_message
            if cost:
                notification.cost = cost
            db.commit()
            return True
        return False
    except Exception as e:
        logger.error(f"Error actualizando estado de notificación: {e}")
        db.rollback()
        return False
    finally:
        db.close()

async def _declare_topology(channel: aio_pika.Channel) -> None:
    # Declara exchanges/colas necesarios (principal, reintentos y DLQ)
    ex_type = {
        "direct": aio_pika.ExchangeType.DIRECT,
        "topic": aio_pika.ExchangeType.TOPIC,
        "fanout": aio_pika.ExchangeType.FANOUT,
    }.get(EXCHANGE_TYPE, aio_pika.ExchangeType.DIRECT)
    # 1) Exchange principal donde se publican mensajes normales
    exchange = await channel.declare_exchange(EXCHANGE_NAME, ex_type, durable=True)

    # 2) DLX/DLQ para fallos definitivos (tras agotar reintentos)
    dlx = await channel.declare_exchange(f"{EXCHANGE_NAME}.dlx", aio_pika.ExchangeType.FANOUT, durable=True)
    dlq = await channel.declare_queue(f"{QUEUE_NAME}.dlq", durable=True)
    await dlq.bind(dlx)

    # 3) Exchanges/colas de reintento con TTL. Tras expirar el TTL, el mensaje vuelve
    #    al exchange principal y el worker lo consumirá de nuevo.
    for idx, delay_sec in enumerate(RETRY_DELAYS, start=1):
        retry_exchange = await channel.declare_exchange(f"{EXCHANGE_NAME}.retry.{idx}", aio_pika.ExchangeType.DIRECT, durable=True)
        retry_queue = await channel.declare_queue(
            f"{QUEUE_NAME}.retry.{idx}",
            durable=True,
            arguments={
                "x-dead-letter-exchange": EXCHANGE_NAME,          # after TTL, return to main exchange
                "x-message-ttl": delay_sec * 1000,                # ms
            },
        )
        await retry_queue.bind(retry_exchange, ROUTING_KEY)

    # 4) Cola principal desde la que el worker consume. Si el mensaje ya agotó
    #    reintentos, lo enviamos manualmente a DLX.
    main_queue = await channel.declare_queue(
        QUEUE_NAME,
        durable=True,
        arguments={
            "x-dead-letter-exchange": f"{EXCHANGE_NAME}.dlx",
        },
    )
    await main_queue.bind(exchange, ROUTING_KEY)

async def _connect() -> aio_pika.RobustConnection:
    # Crea una conexión robusta a RabbitMQ
    url = f"amqp://{RABBITMQ_USERNAME}:{RABBITMQ_PASSWORD}@{RABBITMQ_HOST}:{RABBITMQ_PORT}/{RABBITMQ_VHOST}"
    return await aio_pika.connect_robust(url)

async def _publish_to_retry(channel: aio_pika.Channel, retry_index: int, payload: Dict[str, Any], headers: Dict[str, Any]) -> None:
    # Con infraestructura completa: usar colas de retry con TTL
    if DECLARE_INFRA:
        retry_exchange_name = f"{EXCHANGE_NAME}.retry.{retry_index}"
        exchange = await channel.declare_exchange(retry_exchange_name, aio_pika.ExchangeType.DIRECT, durable=True)
        body = json.dumps(payload).encode("utf-8")
        msg = aio_pika.Message(
            body=body,
            content_type="application/json",
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            headers=headers,
        )
        await exchange.publish(msg, routing_key=ROUTING_KEY)
        return
    # Modo compatibilidad: espera en el worker y republica al exchange principal
    retry_delay = RETRY_DELAYS[max(0, retry_index - 1)]
    await asyncio.sleep(retry_delay)
    # No redeclarar el exchange principal; usar el existente para evitar conflictos con definiciones pre-cargadas
    main_exchange = await channel.get_exchange(EXCHANGE_NAME)
    body = json.dumps(payload).encode("utf-8")
    msg = aio_pika.Message(
        body=body,
        content_type="application/json",
        delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
        headers=headers,
    )
    await main_exchange.publish(msg, routing_key=ROUTING_KEY)

async def _publish_to_dlq(channel: aio_pika.Channel, payload: Dict[str, Any], headers: Dict[str, Any]) -> None:
    # Publicar en DLX existente para evitar conflictos de parámetros
    dlx = await channel.get_exchange(DLX_NAME)
    body = json.dumps(payload).encode("utf-8")
    msg = aio_pika.Message(
        body=body,
        content_type="application/json",
        delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
        headers=headers,
    )
    # Usar routing_key vacío por compatibilidad con fanout; para topic/direct no afecta si no hay bindings específicos
    await dlx.publish(msg, routing_key="")

async def _process_one(payload: Dict[str, Any]) -> None:
    """Procesa un único mensaje.

    Soporta dos formatos:
    1. Formato simple (un canal):
       - channel: "email" | "sms" | "whatsapp" | "push"
       - destination: destino del mensaje
       - message: contenido principal
       - subject: opcional (para email o push)
    
    2. Formato multi-canal:
       - destination: { "email": "...", "sms": "...", "whatsapp": "...", "push": "..." }
       - message: { "email": "HTML content", "sms": "text", "whatsapp": "text", "push": "text" }
       - subject: opcional (para email o push)
       - metadata: opcional
    """
    # Detectar si es formato multi-canal
    if "destination" in payload and isinstance(payload["destination"], dict):
        await _process_multi_channel(payload)
    else:
        await _process_single_channel(payload)


async def _process_single_channel(payload: Dict[str, Any]) -> None:
    """Procesa mensaje de un solo canal (formato original)"""
    channel_value = payload.get("channel")
    notification_channel = _parse_channel(channel_value)

    destination = payload.get("destination")
    message = payload.get("message")
    subject = payload.get("subject")
    user_id = payload.get("user_id", "system")

    # Guardar notificación en BD antes de enviar
    notification_id = _save_notification_to_db(
        user_id=user_id,
        channel=notification_channel,
        destination=destination,
        message=message,
        subject=subject,
        status=NotificationStatus.PENDING
    )

    if notification_id:
        try:
            ch = create_channel(notification_channel)
            await ch.send(destination=destination, message=message, subject=subject)
            
            # Actualizar estado a enviado
            _update_notification_status(notification_id, NotificationStatus.SENT)
            logger.info(f"Notificación {notification_id} enviada exitosamente por {channel_value} a {destination}")
            
        except Exception as e:
            # Actualizar estado a fallido
            _update_notification_status(notification_id, NotificationStatus.FAILED, str(e))
            logger.error(f"Error enviando notificación {notification_id}: {e}")
            raise
    else:
        logger.error("No se pudo guardar la notificación en BD")
        raise Exception("Error guardando notificación en BD")


async def _process_multi_channel(payload: Dict[str, Any]) -> None:
    """Procesa mensaje de múltiples canales con mensajes específicos por canal"""
    destination_dict = payload.get("destination", {})
    message_dict = payload.get("message", {})
    subject = payload.get("subject")
    metadata = payload.get("metadata", {})
    user_id = payload.get("user_id", "system")

    # Procesar cada canal que tenga tanto destino como mensaje
    for channel_name, destination_value in destination_dict.items():
        if destination_value and channel_name in message_dict:
            message_value = message_dict[channel_name]
            if message_value:  # Solo procesar si hay mensaje
                try:
                    notification_channel = _parse_channel(channel_name)
                    
                    # Guardar notificación en BD antes de enviar
                    notification_id = _save_notification_to_db(
                        user_id=user_id,
                        channel=notification_channel,
                        destination=destination_value,
                        message=message_value,
                        subject=subject,
                        status=NotificationStatus.PENDING
                    )
                    
                    if notification_id:
                        ch = create_channel(notification_channel)
                        await ch.send(destination=destination_value, message=message_value, subject=subject)
                        
                        # Actualizar estado a enviado
                        _update_notification_status(notification_id, NotificationStatus.SENT)
                        logger.info(f"Notificación {notification_id} enviada por {channel_name} a {destination_value}")
                    else:
                        logger.error(f"No se pudo guardar notificación para {channel_name}")
                        
                except Exception as exc:
                    # Actualizar estado a fallido si hay notification_id
                    if 'notification_id' in locals():
                        _update_notification_status(notification_id, NotificationStatus.FAILED, str(exc))
                    logger.error(f"Error enviando por {channel_name} a {destination_value}: {exc}")
                    # Continuar con otros canales aunque uno falle

async def main() -> None:
    # Bucle principal del worker: consume, procesa, reintenta o manda a DLQ
    connection = await _connect()
    async with connection:
        channel = await connection.channel()
        await channel.set_qos(prefetch_count=10)
        if DECLARE_INFRA:
            await _declare_topology(channel)

        # Usamos get_queue para no redeclarar con argumentos diferentes
        queue = await channel.get_queue(QUEUE_NAME)

        async with queue.iterator() as queue_iter:
            async for incoming in queue_iter:
                try:
                    body = incoming.body.decode("utf-8")
                    payload = json.loads(body)

                    await _process_one(payload)

                    await incoming.ack()
                    logger.info("Mensaje procesado correctamente")
                except Exception as exc:
                    logger.error(f"Error procesando mensaje: {exc}")

                    # Determine current retry count
                    headers = dict(incoming.headers or {})
                    current_retry = int(headers.get("x-retry-count", 0))
                    payload_for_retry = payload if 'payload' in locals() else {}
                    await incoming.ack()  # prevent immediate re-delivery

                    if current_retry < MAX_RETRIES:
                        next_retry = current_retry + 1
                        headers["x-retry-count"] = next_retry
                        await _publish_to_retry(channel, next_retry, payload_for_retry, headers)
                        logger.warning(f"Reintentando mensaje, intento {next_retry}/{MAX_RETRIES}")
                    else:
                        headers["x-final-failure"] = True
                        await _publish_to_dlq(channel, payload_for_retry, headers)
                        logger.error("Mensaje enviado a DLQ tras agotar reintentos")

if __name__ == "__main__":
    asyncio.run(main())