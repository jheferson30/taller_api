"""
Modelo SQLAlchemy para la entidad Notificacion.

Representa una notificación interna persistente dirigida a un usuario específico
dentro de un taller. Soporta dos tipos: asignación de ticket y alerta de renovación de plan.

Invariante multi-tenant: taller_id siempre coincide con el taller del destinatario.
"""

import enum

from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, Index, Integer, String
from sqlalchemy.sql import func

from app.configuracion.base_datos import Base


class TipoNotificacion(enum.StrEnum):
    """
    Tipos de notificación interna del sistema.

    - TICKET_ASIGNADO: Notifica al mecánico que se le asignó un ticket.
    - RENOVACION_PLAN: Notifica al ADMIN que el plan SaaS está próximo a vencer.
    - MENSAJE_PLATAFORMA: Mensaje del SUPER_ADMIN a todos los talleres.
    """

    TICKET_ASIGNADO = "TICKET_ASIGNADO"
    RENOVACION_PLAN = "RENOVACION_PLAN"
    MENSAJE_PLATAFORMA = "MENSAJE_PLATAFORMA"


class Notificacion(Base):
    """
    Notificación interna persistente en base de datos.

    Cada notificación pertenece a un taller (tenant) y está dirigida a un usuario
    específico dentro de ese taller. El campo taller_id es un invariante de
    aislamiento multi-tenant: nunca puede diferir del taller del destinatario.
    """

    __tablename__ = "notificaciones"

    id = Column(Integer, primary_key=True, index=True)
    taller_id = Column(
        Integer, ForeignKey("talleres.id"), nullable=False, index=True
    )
    destinatario_user_id = Column(
        Integer, ForeignKey("users.id"), nullable=False, index=True
    )
    tipo = Column(Enum(TipoNotificacion), nullable=False, index=True)
    titulo = Column(String(200), nullable=False)
    mensaje = Column(String(500), nullable=False)
    leida = Column(Boolean, default=False, nullable=False, index=True)
    fecha_creacion = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    # Referencia al recurso relacionado: ticket_id para TICKET_ASIGNADO,
    # taller_id para RENOVACION_PLAN
    referencia_id = Column(Integer, nullable=True)

    __table_args__ = (
        # Índice compuesto optimizado para la query más frecuente (badge polling)
        Index(
            "ix_notificaciones_tenant_user_leida",
            "taller_id",
            "destinatario_user_id",
            "leida",
        ),
    )
