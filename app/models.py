from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, Enum
from sqlalchemy.orm import declarative_base
from sqlalchemy import func
from datetime import datetime
from pydantic import BaseModel
import enum

#Este archivo tendra las representaciones de las tablas de la base de datos

#Esto lo que hace es crear la "base" para todos lo modelos (es como una plantilla para los modelos)
Base = declarative_base()

#Enum para los estados de la notificacion
class NotificationStatus(str, enum.Enum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    SCHEDULED = "scheduled"
    CANCELLED = "cancelled"

#Enum para los canales de notificacion (Debemos establecer si vamos a usar uno en especifico o varios)
class NotificationChannel(str, enum.Enum):
    EMAIL = "email"
    SMS = "sms"
    WHATSAPP = "whatsapp"
    PUSH = "push"

#Modelo para la tabla de notificaciones
class Notification(Base):
    __tablename__ = "notifications"

    #Columnas de la tabla
    id = Column(Integer, primary_key=True, index=True) 
    user_id = Column(String(100), nullable=False, index=True) #id del usuario que recibira la notificacion
    channel = Column(Enum(NotificationChannel), nullable=False) #canal de notificacion (email, sms, whatsapp, push)
    destination = Column(String(255), nullable=False) #destino de la notificacion (email, numero de telefono, whatsapp, push)
    subject = Column(String(255), nullable=True) #asunto de la notificacion (solo para email)
    message = Column(Text, nullable=False) #mensaje de la notificacion
    status = Column(Enum(NotificationStatus), default=NotificationStatus.PENDING) #estado de la notificacion (pending, sent, failed, scheduled)
   
    #Fechas
    created_at = Column(DateTime(timezone=True), server_default=func.now()) #fecha de creacion de la notificacion
    scheduled_at = Column(DateTime(timezone=True), nullable=True) #Cuando se debera enviar la notificacion
    sent_at = Column(DateTime(timezone=True), nullable=True) #Cuando se envio la notificacion realmente

    #Metadatos adicionales
    retry_count = Column(Integer, default=0) #cantidad de reintentos de envio de la notificacion
    error_message = Column(Text, nullable=True) #mensaje de error en caso de fallo
    cost = Column(String(20), nullable=True) #costo de la notificacion 

#Modelo para la tabla de canales disponibles
class NotificationChannelConfig(Base):
    __tablename__ = "notification_channels"

    id = Column(Integer, primary_key=True, index=True) #id del canal de notificacion
    name = Column(Enum(NotificationChannel), unique=True, nullable=False) #nombre del canal de notificacion
    enabled = Column(Boolean, default=True) #si el canal esta habilitado
    config = Column(Text, nullable=True) #configuracion del JSON del canal
    created_at = Column(DateTime(timezone=True), server_default=func.now()) #fecha de creacion del canal
    updated_at = Column(DateTime(timezone=True), onupdate=func.now()) #fecha de actualizacion del canal

#Modelo para la tabla de metricas de notificaciones
class NotificationMetrics(Base):
    __tablename__ = "notification_metrics"

    id = Column(Integer, primary_key=True) #id de la metrica de notificacion
    channel = Column(Enum(NotificationChannel), nullable=False) #canal de notificacion
    total_sent = Column(Integer, default=0) #cantidad de notificaciones enviadas
    total_failed = Column(Integer, default=0) #cantidad de notificaciones fallidas
    total_pending = Column(Integer, default=0) #cantidad de notificaciones pendientes
    date = Column(DateTime(timezone=True), server_default=func.now()) #fecha de la metrica

# Modelo para la tabla de usuarios (requerido para autenticación JWT)
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class NotifyPayload(BaseModel):
    destination: str
    message: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str