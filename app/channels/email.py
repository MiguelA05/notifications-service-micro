from typing import Optional
from .base import Channel
import logging
logger = logging.getLogger(__name__)

class EmailChannel(Channel):
    name = "email"

    async def send(self, destination: str, message: str, subject: Optional[str] = None) -> None:
        logger.info(f"Enviando {self.name} a {destination}")
        #TODO Aqui se valida email y se llama al proveedor
        #Esto es una simulacion de envio de email
        if not destination or "@" not in destination:
            raise ValueError("Email invalido")
        #Simulacion de envio de email
        return