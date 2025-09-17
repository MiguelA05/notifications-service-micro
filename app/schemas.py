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


class NotificationBase(BaseModel):
    channel: ChannelName = Field(..., description="Canal de envío")
    destination: str = Field(..., description="Destino del mensaje")
    message: str = Field(..., min_length=1)
    subject: Optional[str] = None

    @validator("destination")
    def validate_destination(cls, v: str, values):  # noqa: N805
        channel = values.get("channel")
        if channel == "email":
            EmailStr.validate(v)
        # Para sms/whatsapp/push podríamos agregar validaciones específicas
        return v


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
