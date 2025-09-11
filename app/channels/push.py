from typing import Any, Optional, Dict, List
from .base import Channel
import logging
import json
from datetime import datetime

class PushChannel(Channel):
    name = "push"
    
    def __init__(self, config: dict = None):
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        self.provider = self.config.get("provider", "firebase")
        
        # Configuración de Firebase
        self.firebase_project_id = self.config.get("firebase_project_id", "")
        self.firebase_service_account_key = self.config.get("firebase_service_account_key", "")
        
        # Configuración de Web Push
        self.web_vapid_public_key = self.config.get("web_vapid_public_key", "")
        self.web_vapid_private_key = self.config.get("web_vapid_private_key", "")
        
        # Validar configuración
        if self.provider == "firebase" and not self.firebase_project_id:
            self.logger.warning("Firebase configurado, pero sin Project ID")
    
    def validate_destination(self, destination: str) -> str:
        """
        Valida que el token de dispositivo sea válido
        
        Args:
            destination: Token del dispositivo a validar
            
        Returns:
            str: Token validado
            
        Raises:
            ValueError: Si el token no es válido
        """
        if not destination or len(destination) < 10:
            raise ValueError(f"Token de dispositivo inválido: {destination}")
        
        # Validar formato básico del token
        if not isinstance(destination, str):
            raise ValueError(f"Token debe ser string: {destination}")
        
        self.logger.info(f"Token de dispositivo validado: {destination[:20]}...")
        return destination
    
    async def send(self, destination: str, message: str, subject: str = None) -> None:
        """
        Envía una notificación push
        
        Args:
            destination: Token del dispositivo
            message: Mensaje de la notificación
            subject: Título de la notificación (opcional)
        """
        try:
            destination = self.validate_destination(destination)
            
            # Crear payload básico
            payload = {
                "title": subject or "Notificación",
                "body": message,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            if self.provider == "firebase":
                await self._send_via_firebase(destination, payload)
            else:
                raise ValueError(f"Proveedor no soportado: {self.provider}")
                
        except Exception as e:
            self.logger.error(f"Error enviando push: {str(e)}")
            raise
    
    async def _send_via_firebase(self, token: str, payload: Dict[str, Any]) -> None:
        """Envía notificación via Firebase Cloud Messaging"""
        try:
            # Aquí implementaremos la lógica de Firebase
            self.logger.info(f"Enviando push via Firebase a token: {token[:20]}...")
            self.logger.info(f"Payload: {payload}")
            
            # TODO: Implementar envío real con Firebase
            self.logger.info("✅ Push enviado via Firebase (simulado)")
            
        except Exception as e:
            self.logger.error(f"Error enviando via Firebase: {str(e)}")
            raise
    
    
    async def send_with_data(self, destination: str, title: str, body: str, data: Dict[str, Any] = None) -> None:
        """
        Envía notificación push con datos personalizados
        
        Args:
            destination: Token del dispositivo
            title: Título de la notificación
            body: Cuerpo del mensaje
            data: Datos adicionales (opcional)
        """
        try:
            destination = self.validate_destination(destination)
            
            payload = {
                "title": title,
                "body": body,
                "data": data or {},
                "timestamp": datetime.utcnow().isoformat()
            }
            
            if self.provider == "firebase":
                await self._send_via_firebase(destination, payload)
            else:
                raise ValueError(f"Proveedor no soportado: {self.provider}")
                
        except Exception as e:
            self.logger.error(f"Error enviando push con datos: {str(e)}")
            raise
    
    async def send_to_multiple(self, tokens: List[str], title: str, body: str, data: Dict[str, Any] = None) -> None:
        """
        Envía notificación push a múltiples dispositivos
        
        Args:
            tokens: Lista de tokens de dispositivos
            title: Título de la notificación
            body: Cuerpo del mensaje
            data: Datos adicionales (opcional)
        """
        try:
            if not tokens:
                raise ValueError("Lista de tokens vacía")
            
            payload = {
                "title": title,
                "body": body,
                "data": data or {},
                "timestamp": datetime.utcnow().isoformat()
            }
            
            self.logger.info(f"Enviando push a {len(tokens)} dispositivos")
            
            for token in tokens:
                try:
                    if self.provider == "firebase":
                        await self._send_via_firebase(token, payload)
                except Exception as e:
                    self.logger.error(f"Error enviando a token {token[:20]}...: {str(e)}")
                    # Continuar con el siguiente token
                    continue
                    
            self.logger.info("✅ Push enviado a todos los dispositivos")
            
        except Exception as e:
            self.logger.error(f"Error enviando push múltiple: {str(e)}")
            raise