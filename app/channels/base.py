from abc import ABC, abstractmethod
from typing import Optional

class Channel(ABC):
    name: str #Esto sirve para identificar el canal

    @abstractmethod
    async def send(self, destination: str, message: str, subject: Optional[str] = None) -> None:
        """
        Envia el mensaje al destino por este canal
        Debe lanzar excepcion si fall; no retornar False silenciosamente
        """
        ...
    
    def validate_destination(self, destination: str) -> None:
        """
        Este metodo es mas opcional, valida el destino (puede lanzar ValueError)
        Implementacion baase: no hace nada.
        """
        return

    #Metodo solo para debug que retorna el nombre del canal
    def __str__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name})"
    