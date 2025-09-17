from typing import Optional
import os
from app.models import NotificationChannel
from .base import Channel
from .email import EmailChannel
from .sms import SMSChannel
from .whatsapp import WhatsAppChannel
from .push import PushChannel

_CHANNEL_MAP: dict[NotificationChannel, type[Channel]] = {
    NotificationChannel.EMAIL: EmailChannel,
    NotificationChannel.SMS: SMSChannel,
    NotificationChannel.WHATSAPP: WhatsAppChannel,
    NotificationChannel.PUSH: PushChannel
}

def create_channel(channel_name: NotificationChannel, config: dict = None) -> Channel:
    """
    Crea una instancia del canal de notificacion especificado

    Args:
        channel_name: Tipo del canal de notificacion
        config: Configuracion especifica del canal (opcional)

    Returns:
        Instancia del canal de notificacion
    """
    try:
        channel_cls = _CHANNEL_MAP[channel_name]
    except KeyError:
        raise ValueError(f"Canal de notificacion no valido: {channel_name}")

    # Si no se pasa configuracion, se arma una por defecto desde variables de entorno
    if config is None:
        if channel_name == NotificationChannel.EMAIL:
            # Preferir SendGrid si hay API key, de lo contrario SMTP
            sendgrid_api_key = os.getenv("SENDGRID_API_KEY", "").strip()
            if sendgrid_api_key:
                config = {
                    "provider": "sendgrid",
                    "api_key": sendgrid_api_key,
                    "from_email": os.getenv("FROM_EMAIL", "noreply@example.com"),
                    "from_name": os.getenv("FROM_NAME", "Notification Service"),
                }
            else:
                config = {
                    "provider": "smtp",
                    "smtp_host": os.getenv("SMTP_HOST", "smtp.gmail.com"),
                    "smtp_port": int(os.getenv("SMTP_PORT", "587")),
                    "smtp_user": os.getenv("SMTP_USER"),
                    "smtp_password": os.getenv("SMTP_PASSWORD"),
                    "from_email": os.getenv("FROM_EMAIL", "noreply@example.com"),
                    "from_name": os.getenv("FROM_NAME", "Notification Service"),
                }
        elif channel_name == NotificationChannel.SMS:
            config = {
                "provider": "twilio",
                "account_sid": os.getenv("TWILIO_ACCOUNT_SID", ""),
                "auth_token": os.getenv("TWILIO_AUTH_TOKEN", ""),
                "from_number": os.getenv("TWILIO_FROM_NUMBER", ""),
            }
        elif channel_name == NotificationChannel.WHATSAPP:
            config = {
                "provider": "twilio",
                "account_sid": os.getenv("TWILIO_ACCOUNT_SID", ""),
                "auth_token": os.getenv("TWILIO_AUTH_TOKEN", ""),
                "from_number": os.getenv("TWILIO_WHATSAPP_FROM", ""),
                "webhook_url": os.getenv("WHATSAPP_WEBHOOK_URL", ""),
            }
        elif channel_name == NotificationChannel.PUSH:
            config = {
                "provider": "firebase",
                "firebase_project_id": os.getenv("FIREBASE_PROJECT_ID", ""),
                "firebase_service_account_key": os.getenv("FIREBASE_SERVICE_ACCOUNT_KEY", ""),
                "web_vapid_public_key": os.getenv("WEB_VAPID_PUBLIC_KEY", ""),
                "web_vapid_private_key": os.getenv("WEB_VAPID_PRIVATE_KEY", ""),
            }
        else:
            config = {}
        
    return channel_cls(config)