from typing import Optional
from .base import Channel
import logging
logger = logging.getLogger(__name__)

class PushChannel(Channel):
    name = "push"
    async def send(self, destination: str, message: str, subject: Optional[str] = None) -> None:
        logger.info(f"Enviando {self.name} a {destination}")
        #TODO Aqui se valida el token de push y se llama al proveedor
        #Esto es una simulacion de envio de push
        if not destination or len(destination) < 10:
            raise ValueError("Token de push invalido")
        #Simulacion de envio de push
        return