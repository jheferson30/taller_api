"""
Repositorio de acceso a datos de logs de auditoría.

Este módulo implementa el patrón Repository para abstraer
el acceso a datos de la tabla audit_log.

IMPORTANTE: Los registros de auditoría son INMUTABLES.
Solo se permiten operaciones de creación y lectura.
NO hay métodos update() ni delete().
"""

from typing import List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.modelos.audit_log import AuditLog


class AuditLogRepository:
    """
    Repositorio de acceso a datos de logs de auditoría.
    
    Abstrae todas las operaciones de base de datos relacionadas
    con audit_log. Los registros son inmutables para garantizar
    la integridad del audit trail.
    
    Operaciones permitidas:
    - create: Crear nuevos registros de auditoría
    - read: Consultar registros existentes con filtros y paginación
    
    Operaciones NO permitidas:
    - update: Los registros no pueden modificarse
    - delete: Los registros no pueden eliminarse
    """
    
    def __init__(self, db: Session):
        """
        Inicializa el repositorio con una sesión de base de datos.
        
        Args:
            db: Sesión de SQLAlchemy
        """
        self.db = db
    
    def create(self, audit_log: AuditLog) -> AuditLog:
        """
        Crea un nuevo registro de auditoría en la base de datos.
        
        Los registros de auditoría son inmutables y no pueden
        ser modificados después de su creación.
        
        Args:
            audit_log: Objeto AuditLog a crear
            
        Returns:
            Registro de auditoría creado con ID asignado
        """
        self.db.add(audit_log)
        self.db.commit()
        self.db.refresh(audit_log)
        return audit_log
    
    def get_by_user(
        self,
        user_id: int,
        skip: int = 0,
        limit: int = 100
    ) -> List[AuditLog]:
        """
        Obtiene logs de auditoría de un usuario específico con paginación.
        
        Los resultados se ordenan por timestamp descendente (más recientes primero).
        
        Args:
            user_id: ID del usuario
            skip: Número de registros a saltar (para paginación)
            limit: Número máximo de registros a retornar
            
        Returns:
            Lista de registros de auditoría del usuario
        """
        return (
            self.db.query(AuditLog)
            .filter(AuditLog.user_id == user_id)
            .order_by(AuditLog.timestamp.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    def get_by_action(
        self,
        action: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[AuditLog]:
        """
        Obtiene logs de auditoría por tipo de acción con paginación.
        
        Los resultados se ordenan por timestamp descendente (más recientes primero).
        
        Args:
            action: Tipo de acción (LOGIN, LOGOUT, CREATE, UPDATE, DELETE, etc.)
            skip: Número de registros a saltar (para paginación)
            limit: Número máximo de registros a retornar
            
        Returns:
            Lista de registros de auditoría con la acción especificada
        """
        return (
            self.db.query(AuditLog)
            .filter(AuditLog.action == action)
            .order_by(AuditLog.timestamp.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    def get_by_date_range(
        self,
        start_date: datetime,
        end_date: datetime,
        skip: int = 0,
        limit: int = 100
    ) -> List[AuditLog]:
        """
        Obtiene logs de auditoría en un rango de fechas con paginación.
        
        Los resultados se ordenan por timestamp descendente (más recientes primero).
        
        Args:
            start_date: Fecha y hora de inicio (inclusive)
            end_date: Fecha y hora de fin (inclusive)
            skip: Número de registros a saltar (para paginación)
            limit: Número máximo de registros a retornar
            
        Returns:
            Lista de registros de auditoría en el rango especificado
        """
        return (
            self.db.query(AuditLog)
            .filter(
                and_(
                    AuditLog.timestamp >= start_date,
                    AuditLog.timestamp <= end_date
                )
            )
            .order_by(AuditLog.timestamp.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    # NO HAY MÉTODOS update() o delete()
    # Los registros de auditoría son inmutables por diseño

    def count_by_action_and_ip(
        self,
        action: str,
        ip_address: str,
        since: datetime
    ) -> int:
        """
        Cuenta registros de auditoría por acción e IP desde una fecha.
        
        Útil para detectar patrones de seguridad como intentos de fuerza bruta.
        
        Args:
            action: Tipo de acción (ej: LOGIN_FAILED)
            ip_address: Dirección IP a buscar
            since: Fecha y hora desde la cual contar
            
        Returns:
            Número de registros que coinciden con los criterios
        """
        return (
            self.db.query(AuditLog)
            .filter(
                and_(
                    AuditLog.action == action,
                    AuditLog.ip_address == ip_address,
                    AuditLog.timestamp >= since
                )
            )
            .count()
        )
    
    def count_by_action_and_details(
        self,
        action: str,
        details_key: str,
        details_value: str,
        since: datetime
    ) -> int:
        """
        Cuenta registros de auditoría por acción y valor en details desde una fecha.
        
        Útil para detectar abuso de funcionalidades como password reset.
        
        Args:
            action: Tipo de acción (ej: PASSWORD_RESET)
            details_key: Clave en el campo JSON details
            details_value: Valor a buscar en details[key]
            since: Fecha y hora desde la cual contar
            
        Returns:
            Número de registros que coinciden con los criterios
        """
        return (
            self.db.query(AuditLog)
            .filter(
                and_(
                    AuditLog.action == action,
                    AuditLog.details[details_key].astext == details_value,
                    AuditLog.timestamp >= since
                )
            )
            .count()
        )
