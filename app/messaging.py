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
QUEUE_NAME = os.getenv("AMQP_QUEUE", "notifications.queue")
ROUTING_KEY = os.getenv("AMQP_ROUTING_KEY", "notifications.key")


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
    async with _connection_channel() as channel:
        # Exchange principal
        exchange = await channel.declare_exchange(EXCHANGE_NAME, aio_pika.ExchangeType.DIRECT, durable=True)

        # DLX/DLQ para fallos definitivos (debe coincidir con worker)
        dlx = await channel.declare_exchange(f"{EXCHANGE_NAME}.dlx", aio_pika.ExchangeType.FANOUT, durable=True)
        dlq = await channel.declare_queue(f"{QUEUE_NAME}.dlq", durable=True)
        await dlq.bind(dlx)

        # Cola principal con dead-letter exchange configurado (coincide con worker)
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
        exchange = await channel.declare_exchange(EXCHANGE_NAME, aio_pika.ExchangeType.DIRECT, durable=True)
        body = json.dumps(payload).encode("utf-8")
        message = aio_pika.Message(body=body, content_type="application/json", delivery_mode=aio_pika.DeliveryMode.PERSISTENT)
        await exchange.publish(message, routing_key=routing_key)


