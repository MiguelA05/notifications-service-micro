"""
Cliente para enviar logs a Fluentd de forma síncrona (HTTP) o asíncrona (forward)
"""
import os
import json
import httpx
import logging
from typing import Optional, Dict, Any
from datetime import datetime

FLUENTD_HTTP_URL = os.getenv("FLUENTD_HTTP_URL", "http://fluentd:9880")
FLUENTD_FORWARD_HOST = os.getenv("FLUENTD_FORWARD_HOST", "fluentd")
FLUENTD_FORWARD_PORT = int(os.getenv("FLUENTD_FORWARD_PORT", "24224"))
USE_HTTP = os.getenv("FLUENTD_USE_HTTP", "true").lower() == "true"

logger = logging.getLogger(__name__)

class FluentdClient:
    """Cliente para enviar logs a Fluentd"""
    
    def __init__(self, service_name: str, env: str = "dev"):
        self.service_name = service_name
        self.env = env
        self.http_client = None
        if USE_HTTP:
            self.http_client = httpx.AsyncClient(timeout=2.0)
    
    async def send_log(self, level: str, message: str, **kwargs):
        """
        Envía un log a Fluentd
        
        Args:
            level: Nivel de log (INFO, WARN, ERROR, DEBUG)
            message: Mensaje del log
            **kwargs: Campos adicionales para el log
        """
        log_entry = {
            "time": datetime.utcnow().isoformat() + "Z",
            "service": self.service_name,
            "env": self.env,
            "level": level,
            "msg": message,
            **kwargs
        }
        
        try:
            if USE_HTTP and self.http_client:
                # Envío síncrono vía HTTP
                await self._send_http(log_entry)
            else:
                # Envío asíncrono vía forward (requiere fluent-logger)
                # Por ahora, solo HTTP está implementado
                await self._send_http(log_entry)
        except Exception as e:
            # Si falla el envío a Fluentd, no debe romper la aplicación
            logger.warning(f"Error enviando log a Fluentd: {e}")
    
    async def _send_http(self, log_entry: Dict[str, Any]):
        """Envía log vía HTTP a Fluentd"""
        try:
            # Fluentd HTTP input espera el tag como parte de la URL
            tag = f"{self.service_name}.{log_entry.get('level', 'info').lower()}"
            url = f"{FLUENTD_HTTP_URL}/{tag}"
            
            response = await self.http_client.post(
                url,
                json=log_entry,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
        except Exception as e:
            # Log local si falla
            logger.debug(f"Error en envío HTTP a Fluentd: {e}")
            raise
    
    async def close(self):
        """Cierra el cliente HTTP"""
        if self.http_client:
            await self.http_client.aclose()

# Instancia global (se inicializa en main.py)
fluentd_client: Optional[FluentdClient] = None

def init_fluentd_client(service_name: str, env: str = "dev") -> FluentdClient:
    """Inicializa el cliente de Fluentd"""
    global fluentd_client
    fluentd_client = FluentdClient(service_name, env)
    return fluentd_client

async def log_to_fluentd(level: str, message: str, **kwargs):
    """Función helper para enviar logs a Fluentd"""
    if fluentd_client:
        await fluentd_client.send_log(level, message, **kwargs)

