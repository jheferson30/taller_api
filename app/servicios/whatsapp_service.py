from abc import ABC, abstractmethod
from enum import StrEnum
from typing import Any

from sqlalchemy.orm import Session


class TipoEvento(StrEnum):
    RECEPCION = "RECEPCION"
    FINALIZACION = "FINALIZACION"
    ENTREGA = "ENTREGA"
    MANUAL = "MANUAL"
    ENTRANTE = "ENTRANTE"


class ResultadoEnvio(StrEnum):
    ENVIADO = "ENVIADO"
    ERROR = "ERROR"
    OMITIDO = "OMITIDO"


class WhatsAppService(ABC):
    @abstractmethod
    async def enviar_notificacion(
        self,
        tipo: TipoEvento,
        ticket: Any,  # Ticket SQLAlchemy model
        vehiculo: Any,  # Vehiculo SQLAlchemy model
        db: Session,
    ) -> ResultadoEnvio:
        ...

    @abstractmethod
    async def enviar_mensaje_manual(
        self,
        ticket_id: int,
        telefono: str,
        mensaje: str,
        db: Session,
    ) -> dict:
        ...
