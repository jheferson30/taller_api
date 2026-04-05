"""
Capa de repositorio para acceso a datos.

Este paquete contiene repositorios que abstraen el acceso a la base de datos,
siguiendo el patrón Repository para facilitar testing y reutilización de queries.
"""

from app.repositorios.user_repository import UserRepository
from app.repositorios.role_repository import RoleRepository
from app.repositorios.audit_log_repository import AuditLogRepository
from app.repositorios.token_blacklist_repository import TokenBlacklistRepository
from app.repositorios.password_reset_repository import PasswordResetTokenRepository

__all__ = [
    "UserRepository",
    "RoleRepository",
    "AuditLogRepository",
    "TokenBlacklistRepository",
    "PasswordResetTokenRepository"
]
