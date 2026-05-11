from enum import StrEnum

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.configuracion.base_datos import Base


class AuditAction(StrEnum):
    """Enum de acciones de auditoría."""

    LOGIN = "LOGIN"
    LOGOUT = "LOGOUT"
    LOGIN_FAILED = "LOGIN_FAILED"
    USER_CREATE = "USER_CREATE"
    USER_UPDATE = "USER_UPDATE"
    USER_DEACTIVATE = "USER_DEACTIVATE"
    ROLE_CHANGE = "ROLE_CHANGE"
    PASSWORD_CHANGE = "PASSWORD_CHANGE"
    PASSWORD_RESET = "PASSWORD_RESET"
    TICKET_CREATE = "TICKET_CREATE"
    TICKET_UPDATE = "TICKET_UPDATE"
    TICKET_FINALIZE = "TICKET_FINALIZE"
    CONFIG_CHANGE = "CONFIG_CHANGE"
    SECURITY_ALERT = "SECURITY_ALERT"
    JWT_KEY_ROTATION = "JWT_KEY_ROTATION"
    CROSS_TENANT_ATTEMPT = "CROSS_TENANT_ATTEMPT"
    PII_ACCESS = "PII_ACCESS"
    SECRET_MISSING = "SECRET_MISSING"
    SECURITY_ALERT_DELIVERED = "SECURITY_ALERT_DELIVERED"
    SECURITY_ALERT_FAILED = "SECURITY_ALERT_FAILED"
    # Acciones de gestión de talleres (SUPER_ADMIN)
    TALLER_CREATE = "TALLER_CREATE"
    TALLER_UPDATE = "TALLER_UPDATE"
    TALLER_ACTIVATE = "TALLER_ACTIVATE"
    TALLER_SUSPEND = "TALLER_SUSPEND"
    TALLER_CANCEL = "TALLER_CANCEL"
    TALLER_DEACTIVATE = "TALLER_DEACTIVATE"
    TALLER_EMERGENCY_BLOCK = "TALLER_EMERGENCY_BLOCK"
    TALLER_EMERGENCY_UNBLOCK = "TALLER_EMERGENCY_UNBLOCK"
    PASSWORD_RESET_FORCED = "PASSWORD_RESET_FORCED"
    PASSWORD_RESET_MASS = "PASSWORD_RESET_MASS"
    NOTIFICATION_MASS = "NOTIFICATION_MASS"


class AuditLog(Base):
    """
    Modelo de registro de auditoría inmutable.

    Registra todas las acciones del sistema para trazabilidad y seguridad.
    Los registros NO deben ser modificados o eliminados (audit trail inmutable).
    """

    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    taller_id = Column(
        Integer, ForeignKey("talleres.id", ondelete="SET NULL"), nullable=True, index=True
    )
    action = Column(String(50), nullable=False, index=True)
    resource_type = Column(String(50), nullable=True, index=True)
    resource_id = Column(Integer, nullable=True, index=True)
    ip_address = Column(String(45), nullable=False, index=True)
    user_agent = Column(String(500), nullable=True)
    details = Column(JSON, nullable=True)
    timestamp = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    # Relaciones
    user = relationship("User", back_populates="audit_logs")
