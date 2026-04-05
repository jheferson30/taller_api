"""
Modelos de base de datos del sistema.

Este módulo importa todos los modelos en el orden correcto para evitar
problemas de dependencias circulares en SQLAlchemy.

IMPORTANTE: El orden de importación es crítico. Las tablas intermedias
(como UserRole) deben importarse antes de los modelos que las referencian.
"""

# Importar Base primero
from app.configuracion.base_datos import Base

# Importar tablas intermedias primero (sin relaciones)
from app.modelos.user_role import UserRole

# Importar modelos principales
from app.modelos.role import Role
from app.modelos.user import User
from app.modelos.audit_log import AuditLog
from app.modelos.token_blacklist import TokenBlacklist
from app.modelos.password_reset_token import PasswordResetToken

# Importar otros modelos
from app.modelos.configuracion_seguridad import ConfiguracionSeguridad

__all__ = [
    "Base",
    "User",
    "Role",
    "UserRole",
    "AuditLog",
    "TokenBlacklist",
    "PasswordResetToken",
    "ConfiguracionSeguridad",
]
