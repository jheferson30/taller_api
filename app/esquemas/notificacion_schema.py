"""
Schemas Pydantic para notificaciones internas.

Define los modelos de respuesta para consultas de notificaciones no leídas
y operaciones de marcado como leída.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.modelos.notificacion import TipoNotificacion


class NotificacionRespuesta(BaseModel):
    """
    Respuesta de una notificación individual.

    Incluye todos los campos necesarios para renderizar la notificación
    en la UI: tipo, título, mensaje, estado de lectura y referencia al recurso.
    """

    id: int
    tipo: TipoNotificacion
    titulo: str
    mensaje: str
    leida: bool
    fecha_creacion: datetime
    referencia_id: int | None

    model_config = ConfigDict(from_attributes=True)


class NotificacionesNoLeidasRespuesta(BaseModel):
    """
    Respuesta del endpoint de notificaciones no leídas.

    Incluye el conteo total y la lista de notificaciones para que el badge
    pueda mostrar el número sin necesidad de contar en el cliente.
    """

    total: int
    notificaciones: list[NotificacionRespuesta]
