from abc import ABC, abstractmethod
from enum import Enum


class TipoEvento(str, Enum):
    RECEPCION    = "RECEPCION"
    FINALIZACION = "FINALIZACION"
    ENTREGA      = "ENTREGA"
    MANUAL       = "MANUAL"
    ENTRANTE     = "ENTRANTE"


class ResultadoEnvio(str, Enum):
    ENVIADO  = "ENVIADO"
    ERROR    = "ERROR"
    OMITIDO  = "OMITIDO"


class WhatsAppService(ABC):
    @abstractmethod
    async def enviar_notificacion(
        self,
        tipo: TipoEvento,
        ticket,          # Ticket SQLAlchemy model
        vehiculo,        # Vehiculo SQLAlchemy model
        db,              # Session
    ) -> ResultadoEnvio: ...

    @abstractmethod
    async def enviar_mensaje_manual(
        self,
        ticket_id: int,
        telefono: str,
        mensaje: str,
        db,
    ) -> dict: ...
