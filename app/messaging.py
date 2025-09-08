import os
import json
import asyncio
from contextlib import asynccontextmanager

import aio_pika


RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "localhost")
RABBITMQ_PORT = int(os.getenv("RABBITMQ_PORT", "5672"))
RABBITMQ_USERNAME = os.getenv("RABBITMQ_USERNAME", "admin")
RABBITMQ_PASSWORD = os.getenv("RABBITMQ_PASSWORD", "admin")

EXCHANGE_NAME = os.getenv("AMQP_EXCHANGE", "notifications.exchange")
QUEUE_NAME = os.getenv("AMQP_QUEUE", "notifications.queue")
ROUTING_KEY = os.getenv("AMQP_ROUTING_KEY", "notifications.key")


@asynccontextmanager
async def _connection_channel():
    url = f"amqp://{RABBITMQ_USERNAME}:{RABBITMQ_PASSWORD}@{RABBITMQ_HOST}:{RABBITMQ_PORT}/"
    connection = await aio_pika.connect_robust(url)
    try:
        channel = await connection.channel()
        await channel.set_qos(prefetch_count=10)
        yield channel
    finally:
        await connection.close()


async def setup_infrastructure() -> None:
    async with _connection_channel() as channel:
        exchange = await channel.declare_exchange(EXCHANGE_NAME, aio_pika.ExchangeType.DIRECT, durable=True)
        queue = await channel.declare_queue(QUEUE_NAME, durable=True)
        await queue.bind(exchange, ROUTING_KEY)


async def publish_message(routing_key: str, payload: dict) -> None:
    async with _connection_channel() as channel:
        exchange = await channel.declare_exchange(EXCHANGE_NAME, aio_pika.ExchangeType.DIRECT, durable=True)
        body = json.dumps(payload).encode("utf-8")
        message = aio_pika.Message(body=body, content_type="application/json", delivery_mode=aio_pika.DeliveryMode.PERSISTENT)
        await exchange.publish(message, routing_key=routing_key)


