from typing import Optional
from app.models import NotificationChannel
from .base import Channel
from .email import EmailChannel
from .sms import SmsChannel
from .whatsapp import WhatsappChannel
from .push import PushChannel

_CHANNEL_MAP: dict[NotificationChannel, type[Channel]] = {
    NotificationChannel.EMAIL: EmailChannel,
    NotificationChannel.SMS: SmsChannel,
    NotificationChannel.WHATSAPP: WhatsappChannel,
    NotificationChannel.PUSH: PushChannel
}

def create_channel(channel_name: NotificationChannel) -> Channel:
    try:
        channel_cls = _CHANNEL_MAP[channel_name]
    except KeyError:
        raise ValueError(f"Canal de notificacion no valido: {channel_name}")
    return channel_cls()