from typing import Optional
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

    #Si no se pasa configuracion, se usa la configuracion por defecto
    if config is None:
        config = {}
        
    return channel_cls(config)