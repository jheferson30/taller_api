"""
Modelo SQLAlchemy para la entidad Taller.

Representa un taller mecánico en el sistema multi-tenant.
Cada taller es un tenant independiente con sus propios datos aislados.
"""

import enum

from sqlalchemy import Boolean, Column, DateTime, Enum, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.configuracion.base_datos import Base


class EstadoTaller(enum.StrEnum):
    """
    Estado del ciclo de vida del taller en la plataforma SaaS.

    - TRIAL: Período de prueba gratuita. Acceso completo. Días configurables por SUPER_ADMIN.
    - ACTIVO: Suscripción vigente. Acceso completo.
    - SUSPENDIDO: Pago vencido o suspensión manual. Acceso bloqueado, datos conservados.
    - CANCELADO: Cliente canceló. Datos en retención.
    """

    TRIAL = "TRIAL"
    ACTIVO = "ACTIVO"
    SUSPENDIDO = "SUSPENDIDO"
    CANCELADO = "CANCELADO"


class Taller(Base):
    __tablename__ = "talleres"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(200), unique=True, nullable=False, index=True)
    nit = Column(String(50), nullable=True)
    direccion = Column(String(300), nullable=True)
    telefono = Column(String(50), nullable=True)
    whatsapp_phone_number = Column(
        String(50), 
        nullable=True, 
        unique=True, 
        index=True,
        comment="Número de WhatsApp Business en formato E.164 para routing de webhooks multi-tenant"
    )
    activo = Column(Boolean, default=True, nullable=False, index=True)

    # Ciclo de vida del taller
    estado = Column(
        Enum(EstadoTaller),
        default=EstadoTaller.TRIAL,
        nullable=False,
        index=True,
    )
    fecha_inicio_trial = Column(DateTime(timezone=True), nullable=True)
    dias_trial = Column(Integer, nullable=True)
    fecha_suspension = Column(DateTime(timezone=True), nullable=True)
    fecha_cancelacion = Column(DateTime(timezone=True), nullable=True)

    # Bloqueo de emergencia (independiente del estado — tiene prioridad)
    bloqueado_emergencia = Column(Boolean, default=False, nullable=False)
    fecha_bloqueo_emergencia = Column(DateTime(timezone=True), nullable=True)
    motivo_bloqueo_emergencia = Column(String(500), nullable=True)

    # Fecha de vencimiento del plan SaaS (usado por el verificador de renovación)
    fecha_vencimiento_plan = Column(DateTime(timezone=True), nullable=True)

    fecha_creacion = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    fecha_actualizacion = Column(DateTime(timezone=True), onupdate=func.now())

    # Relaciones
    configuracion = relationship("ConfiguracionTaller", back_populates="taller", uselist=False)
    usuarios = relationship("User", back_populates="taller")
