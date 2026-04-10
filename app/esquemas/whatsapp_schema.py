from datetime import datetime

from pydantic import BaseModel, field_validator


class WhatsAppConfigUpdate(BaseModel):
    whatsapp_token: str | None = None
    whatsapp_phone_id: str | None = None
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
    ticket_id: int | None = None
    telefono_destino: str | None = None
    tipo_evento: str
    resultado: str
    error_detalle: str | None = None
    created_at: datetime

    class Config:
        from_attributes = True
