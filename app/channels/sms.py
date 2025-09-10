from typing import Any, Optional, Dict
from .base import Channel
import logging
import re

class SMSChannel(Channel):
    name = "sms"

    def __init__(self, config: dict = None):
        """
        Inicializa el canal de SMS con configuración

        Args:
            config: Diccionario con la configuración del canal
                - provider: Proveedor de SMS (twilio, etc)
                - account_sid: SID de la cuenta de Twilio
                - auth_token: Token de autenticación de Twilio
                - from_number: Número de teléfono de envío
        """
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        
        # Configuraciones por defecto
        self.provider = self.config.get("provider", "twilio")
        self.from_number = self.config.get("from_number", "+1234567890")
        
        # Validar configuración requerida
        if self.provider == "twilio":
            if not self.config.get("account_sid"):
                self.logger.warning("Twilio configurado, pero sin Account SID")
            if not self.config.get("auth_token"):
                self.logger.warning("Twilio configurado, pero sin Auth Token")

    def validate_destination(self, destination: str) -> None:
        """
        Valida que el número de teléfono sea válido
        
        Args:
            destination: Número de teléfono a validar
            
        Raises:
            ValueError: Si el número no es válido
        """
        # Limpiar el número (quitar espacios, guiones, etc.)
        cleaned = re.sub(r'[^\d+]', '', destination)
        
        # Patrones válidos: +1234567890 o 1234567890
        if not re.match(r'^\+?[1-9]\d{1,14}$', cleaned):
            raise ValueError(f"Número de teléfono inválido: {destination}")
        
        self.logger.info(f"Número de teléfono validado: {destination}")

    async def send(self, destination: str, message: str, subject: str = None) -> None:
        """
        Envía un SMS
        
        Args:
            destination: Número de teléfono destino
            message: Contenido del mensaje
            subject: Asunto (no se usa en SMS, pero mantiene compatibilidad)
        """
        try:
            # Validar destino
            self.validate_destination(destination)
            
            # Enviar según el proveedor
            if self.provider == "twilio":
                await self._send_via_twilio(destination, message)
            else:
                raise ValueError(f"Proveedor no soportado: {self.provider}")
                
        except Exception as e:
            self.logger.error(f"Error enviando SMS: {str(e)}")
            raise

    async def _send_via_twilio(self, destination: str, message: str) -> None:
        """
        Envía SMS usando Twilio
        
        Args:
            destination: Número de teléfono destino
            message: Contenido del mensaje
        """
        try:
            from twilio.rest import Client
            
            # Obtener credenciales
            account_sid = self.config.get("account_sid")
            auth_token = self.config.get("auth_token")
            
            if not account_sid or not auth_token:
                raise ValueError("Credenciales de Twilio no configuradas")
            
            # Crear cliente de Twilio
            client = Client(account_sid, auth_token)
            
            # Enviar SMS
            message_obj = client.messages.create(
                body=message,
                from_=self.from_number,
                to=destination
            )
            
            self.logger.info(f"SMS enviado exitosamente. SID: {message_obj.sid}")
            
        except Exception as e:
            self.logger.error(f"Error enviando SMS via Twilio: {str(e)}")
            raise