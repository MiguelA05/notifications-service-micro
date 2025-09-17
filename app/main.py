from app.channels.factory import create_channel
from fastapi import FastAPI, Body, HTTPException, Depends, Request, Query
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel
import asyncio
import logging
import os

from .messaging import publish_message, setup_infrastructure
from .db import get_db, create_tables, init_default_channels, init_default_user
from .auth import (
    create_access_token,
    verify_password,
    get_user_by_username,
    get_user_by_email,
    verify_token,
    create_user,
)
from .models import NotificationChannel, TokenResponse
from .schemas import NotificationFilter, NotificationCreate
from .crud import list_channels, list_notifications, get_notification, create_notification, get_metrics, list_schedules, get_schedule, cancel_schedule


class NotifyPayload(BaseModel):
    destination: str
    message: str


app = FastAPI(title="notifications-service-micro", version="1.0.0")
logger = logging.getLogger(__name__)


@app.on_event("startup")
async def on_startup() -> None:
    # Inicializar base de datos (SQLAlchemy)
    await asyncio.to_thread(create_tables)
    await asyncio.to_thread(init_default_channels)
    await asyncio.to_thread(init_default_user)
    # Inicializar infraestructura de mensajería (RabbitMQ) solo si es necesario
    if os.getenv("MESSAGING_DECLARE_INFRA", "true").lower() == "true":
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
async def send_notification(payload: NotifyPayload, user_id: str = Depends(verify_token)):
    """Endpoint protegido que requiere autenticación JWT"""
    try:
        await publish_message(routing_key="notifications.key", payload=payload.model_dump())
        return {"status": "ok", "sent_by": user_id, "queued": True}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# FASE 5 - Endpoints de consulta y gestión

@app.get("/channels")
def api_list_channels(db: Session = Depends(get_db)):
    return list_channels(db)


@app.get("/notifications")
def api_list_notifications(
    channel: str | None = Query(None),
    status: str | None = Query(None),
    q: str | None = Query(None),
    since: str | None = Query(None),
    until: str | None = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=200),
    db: Session = Depends(get_db),
):
    try:
        nf = NotificationFilter(
            channel=channel,
            status=status,
            q=q,
            since=since,
            until=until,
            page=page,
            size=size,
        )
        return list_notifications(db, nf)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/notifications/{notification_id}")
def api_get_notification(notification_id: int, db: Session = Depends(get_db)):
    item = get_notification(db, notification_id)
    if not item:
        raise HTTPException(status_code=404, detail="Notification not found")
    return item


@app.post("/notifications/schedule")
async def api_schedule_notification(payload: NotificationCreate = Body(...), db: Session = Depends(get_db)):
    try:
        created = await asyncio.to_thread(create_notification, db, payload)
        # Publicación inmediata si no hay schedule_at
        if payload.schedule_at is None:
            await publish_message(routing_key="notifications.key", payload=payload.model_dump())
        else:
            # En un caso real, usaríamos el scheduler para planificar la publicación
            pass
        return created
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/metrics")
def api_metrics(db: Session = Depends(get_db)):
    return get_metrics(db)


# Schedules persistentes

@app.get("/schedules")
def api_list_schedules(page: int = Query(1, ge=1), size: int = Query(20, ge=1, le=200), db: Session = Depends(get_db)):
    return list_schedules(db, page=page, size=size)


@app.get("/schedules/{schedule_id}")
def api_get_schedule(schedule_id: int, db: Session = Depends(get_db)):
    item = get_schedule(db, schedule_id)
    if not item:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return item


@app.delete("/schedules/{schedule_id}")
def api_cancel_schedule(schedule_id: int, db: Session = Depends(get_db)):
    ok = cancel_schedule(db, schedule_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Schedule not found or not cancellable")
    return {"cancelled": True}

@app.post("/login", response_model=TokenResponse)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """Endpoint de login que retorna un token JWT"""
    user = get_user_by_username(db, form_data.username)
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=401, 
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/register")
async def register(
    username: str,
    email: str, 
    password: str,
    db: Session = Depends(get_db)
):
    """Endpoint para registrar nuevos usuarios"""
    # Verificar si el usuario ya existe
    if get_user_by_username(db, username):
        raise HTTPException(status_code=400, detail="Username already registered")
    
    if get_user_by_email(db, email):
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Crear nuevo usuario
    user = create_user(db, username, email, password)
    return {"message": "User created successfully", "user_id": user.id}

@app.post("/webhook/whatsapp")
async def whatsapp_webhook(request: Request):
    """
    Endpoint para recibir webhooks de WhatsApp
    """
    try:
        # Obtener datos del webhook
        form_data = await request.form()
        webhook_data = dict(form_data)
        
        # Procesar webhook
        whatsapp_channel = create_channel(NotificationChannel.WHATSAPP)
        response = await whatsapp_channel.process_webhook(webhook_data)
        
        return {"status": "success", "data": response}
        
    except Exception as e:
        logger.error(f"Error procesando webhook de WhatsApp: {str(e)}")
        return {"status": "error", "message": str(e)}