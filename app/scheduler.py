"""
Scheduler de Notificaciones (Programación de envíos)
===================================================

Qué es este archivo:
- Un proceso independiente que permite programar notificaciones para que se envíen
  en una fecha/hora futura. Cuando llega el momento, publica un mensaje en RabbitMQ
  y el worker se encarga del envío real.

Conceptos clave:
- Scheduler: "agenda" que recuerda ejecutar tareas en momentos específicos.
- Job: la tarea a ejecutar (publicar una notificación en RabbitMQ).
- Trigger: define cuándo se ejecuta un job (aquí usamos un DateTrigger para una
  fecha exacta).

Cómo probarlo:
- Este archivo incluye una función demo() que agenda un envío dentro de N segundos
  (configurable por variable de entorno). Úsalo para entender el flujo completo.

Variables de entorno útiles:
- SCHEDULER_DEMO_DELAY_SEC: segundos en el futuro para ejecutar el ejemplo (por defecto 30).
- SCHEDULER_DEMO_CHANNEL / DESTINATION: canal y destino que usará la demo.
"""

import os
import json
import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger
import aio_pika

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "localhost")
RABBITMQ_PORT = int(os.getenv("RABBITMQ_PORT", "5672"))
RABBITMQ_USERNAME = os.getenv("RABBITMQ_USERNAME", "admin")
RABBITMQ_PASSWORD = os.getenv("RABBITMQ_PASSWORD", "admin")
RABBITMQ_VHOST = os.getenv("RABBITMQ_VHOST", "foro")

EXCHANGE_NAME = os.getenv("AMQP_EXCHANGE", "notifications.exchange")
ROUTING_KEY = os.getenv("AMQP_ROUTING_KEY", "notifications.key")

async def _publish(payload: Dict[str, Any]) -> None:
    # Publica el payload en RabbitMQ para que lo consuma el worker
    url = f"amqp://{RABBITMQ_USERNAME}:{RABBITMQ_PASSWORD}@{RABBITMQ_HOST}:{RABBITMQ_PORT}/{RABBITMQ_VHOST}"
    connection = await aio_pika.connect_robust(url)
    async with connection:
        channel = await connection.channel()
        exchange = await channel.declare_exchange(EXCHANGE_NAME, aio_pika.ExchangeType.DIRECT, durable=True)
        body = json.dumps(payload).encode("utf-8")
        message = aio_pika.Message(
            body=body,
            content_type="application/json",
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
        )
        await exchange.publish(message, routing_key=ROUTING_KEY)
        logger.info("Publicada notificación programada")

async def schedule_once(run_at: datetime, payload: Dict[str, Any]) -> None:
    """Programa una única notificación para `run_at`.

    En producción puedes:
    - Guardar trabajos en BD y levantarlos al iniciar.
    - Exponer un endpoint para crear/cancelar schedules.
    """

    async def job():
        # Trabajo que se ejecutará en la fecha indicada
        await _publish(payload)

    scheduler = AsyncIOScheduler(timezone=timezone.utc)
    scheduler.start()
    scheduler.add_job(job, DateTrigger(run_date=run_at))
    logger.info(f"Notificación agendada para {run_at.isoformat()}")

    # Mantener vivo el scheduler
    while True:
        await asyncio.sleep(60)

async def demo() -> None:
    # Ejemplo: programa una notificación 30s en el futuro (o el valor que definas)
    future_time = datetime.now(timezone.utc) + timedelta(seconds=int(os.getenv("SCHEDULER_DEMO_DELAY_SEC", "30")))
    payload = {
        "channel": os.getenv("SCHEDULER_DEMO_CHANNEL", "email"),
        "destination": os.getenv("SCHEDULER_DEMO_DESTINATION", "test@example.com"),
        "subject": "Notificación Programada",
        "message": "Este mensaje fue programado por el scheduler",
    }
    await schedule_once(future_time, payload)

if __name__ == "__main__":
    asyncio.run(demo())