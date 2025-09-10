from fastapi import FastAPI, Body, HTTPException, Depends
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel
import asyncio

from .messaging import publish_message, setup_infrastructure
from .auth import create_access_token, verify_password, get_user_by_username, verify_token, TokenData
from .db import get_db, create_tables, init_default_channels


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
    
@app.post("/notify-auth")
async def notify_auth(
    payload: NotifyPayload = Body(...),
    token_data: TokenData = Depends(verify_token)  # 🔐 JWT requerido
) -> dict:
    try:
        await publish_message(routing_key="notifications.key", payload=payload.model_dump())
        return {"queued": True, "user": token_data.username}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/login")
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    user = get_user_by_username(db, form_data.username)
    if not user or not verify_password(form_data.password, user.password):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    
    access_token = create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}