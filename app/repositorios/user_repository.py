"""
Repositorio de acceso a datos de usuarios.

Este módulo implementa el patrón Repository para abstraer
el acceso a datos de la tabla users.
"""

from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.modelos.user import User


class UserRepository:
    """
    Repositorio de acceso a datos de usuarios.
    
    Abstrae todas las operaciones de base de datos relacionadas
    con usuarios, facilitando testing y reutilización de queries.
    """
    
    def __init__(self, db: Session):
        """
        Inicializa el repositorio con una sesión de base de datos.
        
        Args:
            db: Sesión de SQLAlchemy
        """
        self.db = db
    
    def get_by_id(self, user_id: int) -> Optional[User]:
        """
        Obtiene un usuario por su ID.
        
        Args:
            user_id: ID del usuario
            
        Returns:
            Usuario si existe, None en caso contrario
        """
        return self.db.query(User).filter(User.id == user_id).first()
    
    def get_by_username(self, username: str) -> Optional[User]:
        """
        Obtiene un usuario por su nombre de usuario.
        
        Args:
            username: Nombre de usuario
            
        Returns:
            Usuario si existe, None en caso contrario
        """
        return self.db.query(User).filter(User.username == username).first()
    
    def get_by_email(self, email: str) -> Optional[User]:
        """
        Obtiene un usuario por su email.
        
        Args:
            email: Email del usuario
            
        Returns:
            Usuario si existe, None en caso contrario
        """
        return self.db.query(User).filter(User.email == email).first()
    
    def get_all(self, skip: int = 0, limit: int = 100, include_inactive: bool = False) -> List[User]:
        """
        Lista usuarios con paginación.
        
        Por defecto solo retorna usuarios activos.
        
        Args:
            skip: Número de registros a saltar (para paginación)
            limit: Número máximo de registros a retornar
            include_inactive: Si True, incluye usuarios inactivos
            
        Returns:
            Lista de usuarios
        """
        query = self.db.query(User)
        
        if not include_inactive:
            query = query.filter(User.is_active == True)
        
        return query.offset(skip).limit(limit).all()
    
    def create(self, user: User) -> User:
        """
        Crea un nuevo usuario en la base de datos.
        
        Args:
            user: Objeto User a crear
            
        Returns:
            Usuario creado con ID asignado
        """
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user
    
    def update(self, user: User) -> User:
        """
        Actualiza un usuario existente.
        
        Args:
            user: Objeto User con cambios
            
        Returns:
            Usuario actualizado
        """
        self.db.commit()
        self.db.refresh(user)
        return user
    
    def delete(self, user_id: int) -> None:
        """
        Desactiva un usuario (soft delete).
        
        No elimina el registro de la base de datos, solo
        marca el usuario como inactivo.
        
        Args:
            user_id: ID del usuario a desactivar
        """
        user = self.get_by_id(user_id)
        if user:
            user.is_active = False
            self.db.commit()
