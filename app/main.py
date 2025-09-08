from fastapi import FastAPI, Body, HTTPException
from pydantic import BaseModel
import asyncio

from .messaging import publish_message


class NotifyPayload(BaseModel):
    destination: str
    message: str


app = FastAPI(title="notifications-service-micro", version="1.0.0")


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


