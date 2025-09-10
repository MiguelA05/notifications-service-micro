from fastapi import FastAPI, Body, HTTPException
from pydantic import BaseModel
import asyncio

from .messaging import publish_message, setup_infrastructure
from .db import create_tables, init_default_channels


class NotifyPayload(BaseModel):
    destination: str
    message: str


app = FastAPI(title="notifications-service-micro", version="1.0.0")


@app.on_event("startup")
async def on_startup() -> None:
    # Inicializar base de datos (SQLAlchemy)
    await asyncio.to_thread(create_tables)
    await asyncio.to_thread(init_default_channels)
    # Inicializar infraestructura de mensajería (RabbitMQ)
    await setup_infrastructure()


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.post("/notify")
async def notify(payload: NotifyPayload = Body(...)) -> dict:
    try:
        await publish_message(routing_key="notifications.key", payload=payload.model_dump())
        return {"queued": True}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


