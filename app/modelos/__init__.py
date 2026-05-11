"""
Modelos de base de datos SQLAlchemy.
"""

# Importar todos los modelos para asegurar que SQLAlchemy los registre correctamente
from app.modelos.audit_log import AuditLog
from app.modelos.configuracion_seguridad import ConfiguracionSeguridad
from app.modelos.password_reset_token import PasswordResetToken
from app.modelos.role import Role
from app.modelos.token_blacklist import TokenBlacklist
from app.modelos.user import User
from app.modelos.user_role import UserRole

__all__ = [
    "AuditLog",
    "ConfiguracionSeguridad",
    "PasswordResetToken",
    "Role",
    "TokenBlacklist",
    "User",
    "UserRole",
]
