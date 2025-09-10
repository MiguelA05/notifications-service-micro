from typing import Any, Optional, Dict, List
from .base import Channel
import logging
import re
import json
from datetime import datetime

class WhatsAppChannel(Channel):
    name = "whatsapp"
    
    def __init__(self, config: dict = None):
        """
        Inicializa el canal de WhatsApp con configuración
        
        Args:
            config: Diccionario con la configuración del canal
                - provider: Proveedor de WhatsApp (twilio, etc)
                - account_sid: SID de la cuenta de Twilio
                - auth_token: Token de autenticación de Twilio
                - from_number: Número de WhatsApp de envío
                - webhook_url: URL del webhook para recibir mensajes
        """
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        
        # Configuraciones por defecto
        self.provider = self.config.get("provider", "twilio")
        self.from_number = self.config.get("from_number", "whatsapp:+1234567890")
        self.webhook_url = self.config.get("webhook_url", "")
        
        # Validar configuración requerida
        if self.provider == "twilio":
            if not self.config.get("account_sid"):
                self.logger.warning("Twilio configurado, pero sin Account SID")
            if not self.config.get("auth_token"):
                self.logger.warning("Twilio configurado, pero sin Auth Token")
    
    def validate_destination(self, destination: str) -> str:
        """
        Valida que el número de WhatsApp sea válido
        
        Args:
            destination: Número de WhatsApp a validar (formato: +1234567890 o whatsapp:+1234567890)
            
        Returns:
            str: Número validado con prefijo whatsapp:
            
        Raises:
            ValueError: Si el número no es válido
        """
        # Limpiar el número (quitar espacios, guiones, etc.)
        cleaned = re.sub(r'[^\d+]', '', destination)
        
        # Remover prefijo whatsapp: si existe
        if cleaned.startswith('whatsapp:'):
            cleaned = cleaned[9:]
        
        # Patrones válidos: +1234567890 o 1234567890
        if not re.match(r'^\+?[1-9]\d{1,14}$', cleaned):
            raise ValueError(f"Número de WhatsApp inválido: {destination}")
        
        # Agregar prefijo whatsapp: si no existe
        if not destination.startswith('whatsapp:'):
            destination = f"whatsapp:{destination}"
        
        self.logger.info(f"Número de WhatsApp validado: {destination}")
        return destination

    async def send(self, destination: str, message: str, subject: str = None) -> None:
        """
        Envía un mensaje de WhatsApp
        
        Args:
            destination: Número de WhatsApp destino
            message: Contenido del mensaje
            subject: Asunto (no se usa en WhatsApp, pero mantiene compatibilidad)
        """
        try:
            # Validar destino
            destination = self.validate_destination(destination)
            
            # Enviar según el proveedor
            if self.provider == "twilio":
                await self._send_via_twilio(destination, message)
            else:
                raise ValueError(f"Proveedor no soportado: {self.provider}")
                
        except Exception as e:
            self.logger.error(f"Error enviando WhatsApp: {str(e)}")
            raise
    
    async def _send_via_twilio(self, destination: str, message: str) -> None:
        """
        Envía mensaje de WhatsApp usando Twilio
        
        Args:
            destination: Número de WhatsApp destino
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
            
            # Enviar mensaje
            message_obj = client.messages.create(
                body=message,
                from_=self.from_number,
                to=destination
            )
            
            self.logger.info(f"WhatsApp enviado exitosamente. SID: {message_obj.sid}")
            
        except Exception as e:
            self.logger.error(f"Error enviando WhatsApp via Twilio: {str(e)}")
            raise
    
    async def send_image(self, destination: str, image_url: str, caption: str = None) -> None:
        """
        Envía una imagen por WhatsApp
        
        Args:
            destination: Número de WhatsApp destino
            image_url: URL de la imagen
            caption: Texto descriptivo de la imagen
        """
        try:
            destination = self.validate_destination(destination)
            
            if self.provider == "twilio":
                await self._send_media_via_twilio(destination, image_url, "image", caption)
            else:
                raise ValueError(f"Proveedor no soportado: {self.provider}")
                
        except Exception as e:
            self.logger.error(f"Error enviando imagen por WhatsApp: {str(e)}")
            raise
    
    async def send_document(self, destination: str, document_url: str, filename: str = None) -> None:
        """
        Envía un documento por WhatsApp
        
        Args:
            destination: Número de WhatsApp destino
            document_url: URL del documento
            filename: Nombre del archivo
        """
        try:
            destination = self.validate_destination(destination)
            
            if self.provider == "twilio":
                await self._send_media_via_twilio(destination, document_url, "document", filename)
            else:
                raise ValueError(f"Proveedor no soportado: {self.provider}")
                
        except Exception as e:
            self.logger.error(f"Error enviando documento por WhatsApp: {str(e)}")
            raise
    
    async def _send_media_via_twilio(self, destination: str, media_url: str, media_type: str, caption: str = None) -> None:
        """
        Envía multimedia por WhatsApp usando Twilio
        
        Args:
            destination: Número de WhatsApp destino
            media_url: URL del archivo multimedia
            media_type: Tipo de media (image, document, audio, video)
            caption: Texto descriptivo
        """
        try:
            from twilio.rest import Client
            
            account_sid = self.config.get("account_sid")
            auth_token = self.config.get("auth_token")
            
            if not account_sid or not auth_token:
                raise ValueError("Credenciales de Twilio no configuradas")
            
            client = Client(account_sid, auth_token)
            
            # Crear mensaje con multimedia
            message_data = {
                'from_': self.from_number,
                'to': destination,
                'media_url': [media_url]
            }
            
            # Agregar caption si existe
            if caption:
                message_data['body'] = caption
            
            message_obj = client.messages.create(**message_data)
            
            self.logger.info(f"Multimedia {media_type} enviado exitosamente. SID: {message_obj.sid}")
            
        except Exception as e:
            self.logger.error(f"Error enviando multimedia via Twilio: {str(e)}")
            raise

    async def process_webhook(self, webhook_data: dict) -> dict:
        """
        Procesa webhooks de WhatsApp
        
        Args:
            webhook_data: Datos del webhook
            
        Returns:
            dict: Respuesta procesada
        """
        try:
            # Extraer información del mensaje
            message_sid = webhook_data.get('MessageSid')
            from_number = webhook_data.get('From')
            to_number = webhook_data.get('To')
            body = webhook_data.get('Body', '')
            media_count = int(webhook_data.get('NumMedia', 0))
            
            # Procesar multimedia si existe
            media_urls = []
            if media_count > 0:
                for i in range(media_count):
                    media_url = webhook_data.get(f'MediaUrl{i}')
                    if media_url:
                        media_urls.append(media_url)
            
            # Crear respuesta
            response = {
                'message_sid': message_sid,
                'from': from_number,
                'to': to_number,
                'body': body,
                'media_count': media_count,
                'media_urls': media_urls,
                'timestamp': datetime.utcnow().isoformat()
            }
            
            self.logger.info(f"Webhook procesado: {message_sid}")
            return response
            
        except Exception as e:
            self.logger.error(f"Error procesando webhook: {str(e)}")
            raise