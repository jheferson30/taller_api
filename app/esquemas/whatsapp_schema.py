from datetime import datetime
from typing import Optional

from pydantic import BaseModel, field_validator


class WhatsAppConfigUpdate(BaseModel):
    whatsapp_token: Optional[str] = None
    whatsapp_phone_id: Optional[str] = None
    whatsapp_enabled: bool = False


class MensajeManualRequest(BaseModel):
    mensaje: str

    @field_validator("mensaje")
    @classmethod
    def validar_longitud(cls, v):
        if len(v) < 1 or len(v) > 1024:
            raise ValueError("El mensaje debe tener entre 1 y 1024 caracteres")
        return v


class LogNotificacionResponse(BaseModel):
    id: int
    ticket_id: Optional[int] = None
    telefono_destino: Optional[str] = None
    tipo_evento: str
    resultado: str
    error_detalle: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
