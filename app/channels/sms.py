from typing import Optional
from .base import Channel
import logging
logger = logging.getLogger(__name__)

class SmsChannel(Channel):
    name = "sms"

    async def send(self, destination: str, message: str, subject: Optional[str] = None) -> None:
        logger.info(f"Enviando {self.name} a {destination}")
        #TODO Aqui se valida el numero de telefono y se llama al proveedor
        #Esto es una simulacion de envio de sms
        if not destination or not destination.startswith("+") or len(destination) != 12:
            raise ValueError("Numero de telefono invalido")
        #Simulacion de envio de sms
        return