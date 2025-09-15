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
