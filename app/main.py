from app.channels.factory import create_channel
from fastapi import FastAPI, Body, HTTPException, Depends
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel
import asyncio

from .messaging import publish_message, setup_infrastructure
from .db import get_db, create_tables, init_default_channels, init_default_user
from .auth import create_access_token, verify_password, get_user_by_username, verify_token, create_user
from .models import NotificationChannel, TokenResponse


class NotifyPayload(BaseModel):
    destination: str
    message: str


app = FastAPI(title="notifications-service-micro", version="1.0.0")


@app.on_event("startup")
async def on_startup() -> None:
    # Inicializar base de datos (SQLAlchemy)
    await asyncio.to_thread(create_tables)
    await asyncio.to_thread(init_default_channels)
    await asyncio.to_thread(init_default_user)
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
async def send_notification(payload: NotifyPayload, user_id: str = Depends(verify_token)):
    """Endpoint protegido que requiere autenticación JWT"""
    try:
        await publish_message(routing_key="notifications.key", payload=payload.model_dump())
        return {"status": "ok", "sent_by": user_id, "queued": True}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

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