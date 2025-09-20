from __future__ import annotations

from typing import Optional, Literal, List
from datetime import datetime
from pydantic import BaseModel, Field, EmailStr, validator
from pydantic import ConfigDict


class PageMeta(BaseModel):
    page: int = Field(1, ge=1)
    size: int = Field(20, ge=1, le=200)
    total: int = Field(0, ge=0)


class PaginatedResponse(BaseModel):
    items: list
    meta: PageMeta


ChannelName = Literal["email", "sms", "whatsapp", "push"]


class ChannelInfo(BaseModel):
    name: ChannelName
    enabled: bool
    provider: Optional[str] = None


class MultiChannelDestination(BaseModel):
    """Destinos para múltiples canales"""
    email: Optional[EmailStr] = None
    sms: Optional[str] = None
    whatsapp: Optional[str] = None
    push: Optional[str] = None

    def get_active_channels(self) -> list[ChannelName]:
        """Retorna los canales que tienen destino configurado"""
        active = []
        if self.email:
            active.append("email")
        if self.sms:
            active.append("sms")
        if self.whatsapp:
            active.append("whatsapp")
        if self.push:
            active.append("push")
        return active


class NotificationBase(BaseModel):
    channel: ChannelName = Field(..., description="Canal de envío")
    destination: str = Field(..., description="Destino del mensaje")
    message: str = Field(..., min_length=1)
    subject: Optional[str] = None

    @validator("destination")
    def validate_destination(cls, v: str, values):  # noqa: N805
        channel = values.get("channel")
        if channel == "email":
            # En Pydantic V2, la validación de email se hace automáticamente
            # Solo verificamos que no esté vacío
            if not v or not v.strip():
                raise ValueError("Email destination cannot be empty")
        # Para sms/whatsapp/push podríamos agregar validaciones específicas
        return v


class MultiChannelMessage(BaseModel):
    """Mensajes específicos por canal"""
    email: Optional[str] = Field(None, description="Mensaje HTML para email")
    sms: Optional[str] = Field(None, description="Mensaje de texto para SMS")
    whatsapp: Optional[str] = Field(None, description="Mensaje de texto para WhatsApp")
    push: Optional[str] = Field(None, description="Mensaje de texto para Push")

    def get_message_for_channel(self, channel: str) -> Optional[str]:
        """Obtiene el mensaje específico para un canal"""
        return getattr(self, channel, None)

    def get_active_channels(self) -> list[ChannelName]:
        """Retorna los canales que tienen mensaje configurado"""
        active = []
        if self.email:
            active.append("email")
        if self.sms:
            active.append("sms")
        if self.whatsapp:
            active.append("whatsapp")
        if self.push:
            active.append("push")
        return active


class MultiChannelNotification(BaseModel):
    """Notificación que puede enviarse por múltiples canales con mensajes específicos"""
    destination: MultiChannelDestination = Field(..., description="Destinos por canal")
    message: MultiChannelMessage = Field(..., description="Mensajes específicos por canal")
    subject: Optional[str] = Field(None, description="Asunto (para email/push)")
    metadata: Optional[dict] = Field(None, description="Metadatos adicionales")

    def get_notifications(self) -> list[NotificationBase]:
        """Convierte la notificación multi-canal en notificaciones individuales"""
        notifications = []
        destination_channels = self.destination.get_active_channels()
        message_channels = self.message.get_active_channels()
        
        # Solo procesar canales que tengan tanto destino como mensaje
        active_channels = [ch for ch in destination_channels if ch in message_channels]
        
        for channel in active_channels:
            destination_value = getattr(self.destination, channel)
            message_value = self.message.get_message_for_channel(channel)
            
            # Convertir EmailStr a string si es necesario
            destination_str = str(destination_value) if destination_value else ""
            message_str = str(message_value) if message_value else ""
            
            notifications.append(NotificationBase(
                channel=channel,
                destination=destination_str,
                message=message_str,
                subject=self.subject
            ))
        
        return notifications


class NotificationCreate(NotificationBase):
    schedule_at: Optional[datetime] = Field(
        None,
        description="Fecha/hora UTC para programar. Si no, envío inmediato.",
        alias="schedule_at",
    )
    model_config = ConfigDict(populate_by_name=True)


class NotificationDB(NotificationBase):
    id: int
    status: Literal["pending", "scheduled", "processing", "sent", "failed"]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class NotificationFilter(BaseModel):
    channel: Optional[ChannelName] = None
    status: Optional[Literal["pending", "scheduled", "processing", "sent", "failed"]] = None
    q: Optional[str] = Field(None, description="Búsqueda por destino o mensaje")
    since: Optional[datetime] = None
    until: Optional[datetime] = None
    page: int = Field(1, ge=1)
    size: int = Field(20, ge=1, le=200)


class MetricsSummary(BaseModel):
    total_notifications: int
    sent: int
    failed: int
    scheduled: int
    in_process: int
    per_channel: dict[str, int]

# app/schemas.py
from pydantic import BaseModel, EmailStr
from typing import List, Optional
from datetime import datetime
from app.models import NotificationStatus, NotificationChannel

# -----------------------------
# Usuario
# -----------------------------
class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str

class UserOut(BaseModel):
    id: int
    username: str
    email: EmailStr
    is_active: bool
    created_at: Optional[datetime]

    class Config:
        orm_mode = True  # Permite convertir desde objetos ORM (SQLAlchemy)

# -----------------------------
# Token JWT
# -----------------------------
class TokenResponse(BaseModel):
    access_token: str
    token_type: str

# -----------------------------
# Notificaciones
# -----------------------------
class NotificationCreate(BaseModel):
    user_id: str
    channel: NotificationChannel
    destination: str
    subject: Optional[str] = None
    message: str
    scheduled_at: Optional[datetime] = None

class NotificationOut(BaseModel):
    id: int
    user_id: str
    channel: NotificationChannel
    destination: str
    subject: Optional[str]
    message: str
    status: NotificationStatus
    created_at: Optional[datetime]
    scheduled_at: Optional[datetime]
    sent_at: Optional[datetime]
    retry_count: Optional[int]
    error_message: Optional[str]
    cost: Optional[str]

    class Config:
        orm_mode = True

# -----------------------------
# Paginación de notificaciones
# -----------------------------
class PaginatedNotifications(BaseModel):
    items: List[NotificationOut]
    total: int
    page: int
    page_size: int
    total_pages: int
