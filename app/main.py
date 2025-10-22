from app.channels.factory import create_channel
from fastapi import FastAPI, Body, HTTPException, Depends, Request, Query
from fastapi.security import OAuth2PasswordRequestForm
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional
import asyncio
import logging
import structlog
import importlib

def try_configure_logging(service_name: str, env: str = "dev") -> None:
    try:
        logging_config = importlib.import_module("app.logging_config")
        getattr(logging_config, "configure_logging")(service_name=service_name, env=env)
    except Exception:
        import sys
        logging.basicConfig(level=logging.INFO, stream=sys.stdout)
import os
import json

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
from .schemas import NotificationFilter, NotificationCreate, MultiChannelNotification
from .crud import list_channels, list_notifications, get_notification, create_notification, get_metrics, list_schedules, get_schedule, cancel_schedule


class NotifyPayload(BaseModel):
    channel: str = Field(..., description="Canal de envío (email, sms, whatsapp, push)")
    destination: str = Field(..., description="Destino del mensaje")
    message: str = Field(..., min_length=1, description="Mensaje a enviar")
    subject: Optional[str] = Field(None, description="Asunto (para email/push)")
    
    class Config:
        # Configurar para manejar caracteres especiales correctamente
        json_encoders = {
            str: lambda v: v.encode('utf-8').decode('utf-8') if isinstance(v, str) else v
        }


app = FastAPI(
    title="notifications-service-micro", 
    version="1.0.0",
    # Configurar para manejar UTF-8 automáticamente
    openapi_tags=[
        {
            "name": "notifications",
            "description": "Endpoints para envío de notificaciones",
        }
    ]
)

# Agregar prefijo de versión para todos los endpoints
from fastapi import APIRouter

# Crear router con prefijo de versión
v1_router = APIRouter(prefix="/v1")
try_configure_logging(service_name="notifications-service-micro", env=os.getenv("ENV","dev"))
log: structlog.stdlib.BoundLogger = structlog.get_logger()


# Configuración para manejar UTF-8 automáticamente


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


@v1_router.post("/notifications")
async def notify(request: Request) -> dict:
    try:
        # Leer el body como bytes y decodificar con UTF-8
        body_bytes = await request.body()
        body_str = body_bytes.decode('utf-8', errors='ignore')
        
        # Parsear el JSON manualmente
        import json
        payload_dict = json.loads(body_str)
        
        # Validar que tenga los campos requeridos
        required_fields = ['channel', 'destination', 'message']
        for field in required_fields:
            if field not in payload_dict:
                raise HTTPException(status_code=400, detail=f"Campo requerido faltante: {field}")
        
        # Normalizar strings para manejar caracteres especiales
        for key, value in payload_dict.items():
            if isinstance(value, str):
                # Normalizar el string para manejar caracteres especiales
                payload_dict[key] = value.encode('utf-8', errors='ignore').decode('utf-8')
        
        await publish_message(routing_key="notifications.key", payload=payload_dict)
        return {"queued": True}
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"JSON inválido: {str(e)}")
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@v1_router.post("/notifications/multi")
async def notify_multi(request: Request) -> dict:
    """Endpoint para enviar notificaciones por múltiples canales simultáneamente"""
    try:
        # Leer el body como bytes y decodificar con UTF-8
        body_bytes = await request.body()
        body_str = body_bytes.decode('utf-8', errors='ignore')
        
        # Parsear el JSON manualmente
        import json
        payload_dict = json.loads(body_str)
        
        # Validar que tenga los campos requeridos
        required_fields = ['destination', 'message']
        for field in required_fields:
            if field not in payload_dict:
                raise HTTPException(status_code=400, detail=f"Campo requerido faltante: {field}")
        
        # Normalizar strings para manejar caracteres especiales
        def normalize_strings(obj):
            if isinstance(obj, dict):
                return {k: normalize_strings(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [normalize_strings(item) for item in obj]
            elif isinstance(obj, str):
                return obj.encode('utf-8', errors='ignore').decode('utf-8')
            else:
                return obj
        
        payload_dict = normalize_strings(payload_dict)
        
        await publish_message(routing_key="notifications.key", payload=payload_dict)
        return {
            "queued": True, 
            "message": "Notificación encolada para múltiples canales"
        }
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"JSON inválido: {str(e)}")
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@v1_router.post("/notifications/auth")
async def send_notification(payload: NotifyPayload, user_id: str = Depends(verify_token)):
    """Endpoint protegido que requiere autenticación JWT"""
    try:
        await publish_message(routing_key="notifications.key", payload=payload.model_dump())
        return {"status": "ok", "sent_by": user_id, "queued": True}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@v1_router.post("/notifications/multi/auth")
async def send_multi_notification(payload: MultiChannelNotification, user_id: str = Depends(verify_token)):
    """Endpoint protegido para enviar notificaciones por múltiples canales"""
    try:
        worker_payload = {
            "destination": payload.destination.model_dump(),
            "message": payload.message.model_dump(),
            "subject": payload.subject,
            "metadata": payload.metadata
        }
        await publish_message(routing_key="notifications.key", payload=worker_payload)
        return {
            "status": "ok", 
            "sent_by": user_id, 
            "queued": True,
            "channels": payload.destination.get_active_channels(),
            "message_channels": payload.message.get_active_channels()
        }
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
        log.error("whatsapp_webhook_error", error=str(e))
        return {"status": "error", "message": str(e)}

@app.middleware("http")
async def add_request_context(request: Request, call_next):
    # Correlación simple por request
    request_id = request.headers.get("x-request-id") or os.urandom(6).hex()
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(request_id=request_id, path=str(request.url.path), method=request.method)
    try:
        response = await call_next(request)
        return response
    finally:
        structlog.contextvars.clear_contextvars()

@app.on_event("startup")
async def startup():
    log.info("service_started")

@app.on_event("shutdown")
async def shutdown():
    log.info("service_stopped")

# Incluir el router versionado en la aplicación
app.include_router(v1_router)