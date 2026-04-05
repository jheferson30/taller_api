"""
Repositorio de acceso a datos de roles.

Este módulo implementa el patrón Repository para abstraer
el acceso a datos de la tabla roles.
"""

from typing import Optional, List
from sqlalchemy.orm import Session

from app.modelos.role import Role


class RoleRepository:
    """
    Repositorio de acceso a datos de roles.
    
    Abstrae todas las operaciones de base de datos relacionadas
    con roles, facilitando testing y reutilización de queries.
    """
    
    def __init__(self, db: Session):
        """
        Inicializa el repositorio con una sesión de base de datos.
        
        Args:
            db: Sesión de SQLAlchemy
        """
        self.db = db
    
    def get_by_id(self, role_id: int) -> Optional[Role]:
        """
        Obtiene un rol por su ID.
        
        Args:
            role_id: ID del rol
            
        Returns:
            Rol si existe, None en caso contrario
        """
        return self.db.query(Role).filter(Role.id == role_id).first()
    
    def get_by_name(self, name: str) -> Optional[Role]:
        """
        Obtiene un rol por su nombre.
        
        Args:
            name: Nombre del rol (ej: ADMIN, MECANICO)
            
        Returns:
            Rol si existe, None en caso contrario
        """
        return self.db.query(Role).filter(Role.name == name).first()
    
    def get_all(self, skip: int = 0, limit: int = 100) -> List[Role]:
        """
        Lista roles con paginación.
        
        Args:
            skip: Número de registros a saltar (para paginación)
            limit: Número máximo de registros a retornar
            
        Returns:
            Lista de roles
        """
        return self.db.query(Role).offset(skip).limit(limit).all()
    
    def create(self, role: Role) -> Role:
        """
        Crea un nuevo rol en la base de datos.
        
        Args:
            role: Objeto Role a crear
            
        Returns:
            Rol creado con ID asignado
        """
        self.db.add(role)
        self.db.commit()
        self.db.refresh(role)
        return role
    
    def update(self, role: Role) -> Role:
        """
        Actualiza un rol existente.
        
        Args:
            role: Objeto Role con cambios
            
        Returns:
            Rol actualizado
        """
        self.db.commit()
        self.db.refresh(role)
        return role
    
    def delete(self, role_id: int) -> None:
        """
        Elimina un rol de la base de datos.
        
        Args:
            role_id: ID del rol a eliminar
        """
        role = self.get_by_id(role_id)
        if role:
            self.db.delete(role)
            self.db.commit()
