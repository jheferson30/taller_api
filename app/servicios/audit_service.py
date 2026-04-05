"""
Servicio de registro de auditoría.

Este módulo implementa la lógica de negocio para registrar
eventos de auditoría en el sistema. Todos los eventos son
inmutables y se registran con información completa de contexto.
"""

from typing import Optional
from sqlalchemy.orm import Session

from app.modelos.audit_log import AuditLog
from app.repositorios.audit_log_repository import AuditLogRepository


class AuditService:
    """
    Servicio de registro de auditoría.
    
    Maneja el registro de todos los eventos del sistema para
    trazabilidad y seguridad. Los eventos son inmutables y
    contienen información completa de contexto.
    
    Eventos soportados:
    - LOGIN, LOGOUT, LOGIN_FAILED
    - USER_CREATE, USER_UPDATE, USER_DEACTIVATE
    - ROLE_CHANGE
    - PASSWORD_CHANGE, PASSWORD_RESET
    - TICKET_CREATE, TICKET_UPDATE, TICKET_FINALIZE
    - CONFIG_CHANGE
    """
    
    def __init__(self, audit_repo: AuditLogRepository):
        """
        Inicializa el servicio de auditoría.
        
        Args:
            audit_repo: Repositorio de logs de auditoría
        """
        self.audit_repo = audit_repo
    
    def log_event(
        self,
        user_id: Optional[int],
        action: str,
        resource_type: str,
        resource_id: Optional[int],
        ip_address: str,
        user_agent: str,
        details: Optional[dict] = None
    ):
        """
        Registra un evento en el audit trail.
        
        Crea un registro inmutable de auditoría con toda la información
        de contexto necesaria para trazabilidad y análisis de seguridad.
        
        Eventos soportados:
        - LOGIN: Usuario inició sesión exitosamente
        - LOGOUT: Usuario cerró sesión
        - LOGIN_FAILED: Intento fallido de inicio de sesión
        - USER_CREATE: Nuevo usuario creado
        - USER_UPDATE: Usuario actualizado
        - USER_DEACTIVATE: Usuario desactivado
        - ROLE_CHANGE: Roles de usuario modificados
        - PASSWORD_CHANGE: Contraseña cambiada por el usuario
        - PASSWORD_RESET: Contraseña reseteada vía recuperación
        - TICKET_CREATE: Nuevo ticket creado
        - TICKET_UPDATE: Ticket actualizado
        - TICKET_FINALIZE: Ticket finalizado
        - CONFIG_CHANGE: Configuración del sistema modificada
        
        Args:
            user_id: ID del usuario que realiza la acción (None para eventos anónimos)
            action: Tipo de acción realizada
            resource_type: Tipo de recurso afectado (user, ticket, config, etc.)
            resource_id: ID del recurso afectado (None si no aplica)
            ip_address: Dirección IP del cliente
            user_agent: User agent del cliente
            details: Información adicional en formato JSON (opcional)
        """
        audit_log = AuditLog(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            ip_address=ip_address,
            user_agent=user_agent,
            details=details
        )
        
        self.audit_repo.create(audit_log)
