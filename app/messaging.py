import os
import json
import asyncio
from contextlib import asynccontextmanager

import aio_pika


RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "localhost")
RABBITMQ_PORT = int(os.getenv("RABBITMQ_PORT", "5672"))
RABBITMQ_USERNAME = os.getenv("RABBITMQ_USERNAME", "admin")
RABBITMQ_PASSWORD = os.getenv("RABBITMQ_PASSWORD", "admin")
RABBITMQ_VHOST = os.getenv("RABBITMQ_VHOST", "foro")

EXCHANGE_NAME = os.getenv("AMQP_EXCHANGE", "notifications.exchange")
EXCHANGE_TYPE = os.getenv("AMQP_EXCHANGE_TYPE", "direct").lower()  # "direct" | "topic" | "fanout"
QUEUE_NAME = os.getenv("AMQP_QUEUE", "notifications.queue")
ROUTING_KEY = os.getenv("AMQP_ROUTING_KEY", "notifications.key")
DECLARE_INFRA = os.getenv("MESSAGING_DECLARE_INFRA", "true").lower() == "true"


@asynccontextmanager
async def _connection_channel():
    # Conexión incluye vhost (por ejemplo, 'foro')
    url = f"amqp://{RABBITMQ_USERNAME}:{RABBITMQ_PASSWORD}@{RABBITMQ_HOST}:{RABBITMQ_PORT}/{RABBITMQ_VHOST}"
    connection = await aio_pika.connect_robust(url)
    try:
        channel = await connection.channel()
        await channel.set_qos(prefetch_count=10)
        yield channel
    finally:
        await connection.close()


async def setup_infrastructure() -> None:
    if not DECLARE_INFRA:
        return
    async with _connection_channel() as channel:
        # Exchange principal (tipo configurable)
        ex_type = {
            "direct": aio_pika.ExchangeType.DIRECT,
            "topic": aio_pika.ExchangeType.TOPIC,
            "fanout": aio_pika.ExchangeType.FANOUT,
        }.get(EXCHANGE_TYPE, aio_pika.ExchangeType.DIRECT)
        exchange = await channel.declare_exchange(EXCHANGE_NAME, ex_type, durable=True)

        # DLX/DLQ para fallos definitivos (coincidirá con worker si se declara)
        dlx = await channel.declare_exchange(f"{EXCHANGE_NAME}.dlx", aio_pika.ExchangeType.FANOUT, durable=True)
        dlq = await channel.declare_queue(f"{QUEUE_NAME}.dlq", durable=True)
        await dlq.bind(dlx)

        # Cola principal con dead-letter exchange configurado
        queue = await channel.declare_queue(
            QUEUE_NAME,
            durable=True,
            arguments={
                "x-dead-letter-exchange": f"{EXCHANGE_NAME}.dlx",
            },
        )
        await queue.bind(exchange, ROUTING_KEY)


async def publish_message(routing_key: str, payload: dict) -> None:
    async with _connection_channel() as channel:
        # Usar el exchange existente sin redeclararlo para evitar conflictos con definiciones pre-cargadas
        exchange = await channel.get_exchange(EXCHANGE_NAME)
        body = json.dumps(payload).encode("utf-8")
        message = aio_pika.Message(body=body, content_type="application/json", delivery_mode=aio_pika.DeliveryMode.PERSISTENT)
        await exchange.publish(message, routing_key=routing_key)


