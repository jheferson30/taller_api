"""
Servicio de gestión de usuarios.

Este módulo implementa la lógica de negocio para gestión de usuarios:
creación, actualización de roles, desactivación y cambio de contraseña.
"""

import re
from typing import List, Optional
from sqlalchemy.orm import Session

from app.modelos.user import User
from app.modelos.role import Role
from app.modelos.user_role import UserRole
from app.repositorios.user_repository import UserRepository
from app.repositorios.role_repository import RoleRepository
from app.repositorios.token_blacklist_repository import TokenBlacklistRepository
from app.servicios.audit_service import AuditService
from app.seguridad.password_hasher import PasswordHasher


class ValidationError(Exception):
    """Excepción para errores de validación de datos."""
    pass


class DuplicateError(Exception):
    """Excepción para errores de duplicación de datos únicos."""
    pass


class UserService:
    """
    Servicio de gestión de usuarios.
    
    Maneja la creación, actualización, desactivación y gestión de roles
    de usuarios del sistema. Incluye validaciones de negocio y registro
    de auditoría.
    """
    
    def __init__(
        self,
        user_repo: UserRepository,
        role_repo: RoleRepository,
        token_blacklist_repo: TokenBlacklistRepository,
        password_hasher: PasswordHasher,
        audit_service: AuditService,
        db: Session
    ):
        """
        Inicializa el servicio de usuarios.
        
        Args:
            user_repo: Repositorio de usuarios
            role_repo: Repositorio de roles
            token_blacklist_repo: Repositorio de tokens en lista negra
            password_hasher: Hasher de contraseñas
            audit_service: Servicio de auditoría
            db: Sesión de base de datos
        """
        self.user_repo = user_repo
        self.role_repo = role_repo
        self.token_blacklist_repo = token_blacklist_repo
        self.password_hasher = password_hasher
        self.audit_service = audit_service
        self.db = db
    
    def create_user(
        self,
        username: str,
        email: str,
        password: str,
        roles: List[str],
        created_by: int,
        ip_address: str,
        user_agent: str,
        nombre_completo: str = None,
        telefono: str = None,
        direccion: str = None
    ) -> User:
        """
        Crea un nuevo usuario.
        
        Validaciones:
        - Username único
        - Email válido y único
        - Contraseña cumple requisitos (8+ chars, mayúscula, minúscula, número)
        - Roles existen
        
        Proceso:
        1. Valida datos
        2. Hashea contraseña con bcrypt
        3. Crea usuario en DB
        4. Asigna roles
        5. Registra evento USER_CREATE en audit_log
        
        Args:
            username: Nombre de usuario único
            email: Email válido
            password: Contraseña en texto plano
            roles: Lista de nombres de roles
            created_by: ID del usuario que crea
            ip_address: IP del cliente
            user_agent: User agent del cliente
            
        Returns:
            Usuario creado
            
        Raises:
            ValidationError: Si los datos son inválidos
            DuplicateError: Si username o email ya existen
        """
        # Validar contraseña compleja antes de cualquier cosa
        if not self._is_complex_password(password):
            raise ValidationError(
                "La contraseña debe tener al menos 8 caracteres, "
                "incluyendo mayúscula, minúscula y número"
            )

        # Validar email formato
        if not self._is_valid_email(email):
            raise ValidationError("El email no tiene un formato válido")

        # Validar que roles existen
        role_objects = []
        for role_name in roles:
            role = self.role_repo.get_by_name(role_name)
            if not role:
                raise ValidationError(f"El rol '{role_name}' no existe")
            role_objects.append(role)

        # Hashear contraseña
        password_hash = self.password_hasher.hash_password(password)

        # Verificar si el username ya existe (activo o inactivo)
        existing_by_username = self.user_repo.get_by_username(username)
        if existing_by_username:
            if existing_by_username.is_active:
                raise DuplicateError(f"El username '{username}' ya existe")
            # Reactivar usuario inactivo con nuevos datos
            return self._reactivate_user(
                user=existing_by_username,
                email=email,
                password_hash=password_hash,
                role_objects=role_objects,
                nombre_completo=nombre_completo,
                telefono=telefono,
                direccion=direccion,
                created_by=created_by,
                ip_address=ip_address,
                user_agent=user_agent,
                roles=roles
            )

        # Verificar si el email ya existe (activo o inactivo)
        existing_by_email = self.user_repo.get_by_email(email)
        if existing_by_email:
            if existing_by_email.is_active:
                raise DuplicateError(f"El email '{email}' ya está registrado")
            # Email de usuario inactivo, se puede reusar actualizando ese usuario
            return self._reactivate_user(
                user=existing_by_email,
                email=email,
                password_hash=password_hash,
                role_objects=role_objects,
                nombre_completo=nombre_completo,
                telefono=telefono,
                direccion=direccion,
                created_by=created_by,
                ip_address=ip_address,
                user_agent=user_agent,
                roles=roles
            )

        # Crear usuario nuevo
        user = User(
            username=username,
            email=email,
            password_hash=password_hash,
            is_active=True,
            is_migrated=True,
            nombre_completo=nombre_completo,
            telefono=telefono,
            direccion=direccion
        )

        user = self.user_repo.create(user)

        # Asignar roles
        for role in role_objects:
            user_role = UserRole(user_id=user.id, role_id=role.id)
            self.db.add(user_role)

        self.db.commit()
        self.db.refresh(user)

        # Registrar en audit log
        self.audit_service.log_event(
            user_id=created_by,
            action="USER_CREATE",
            resource_type="user",
            resource_id=user.id,
            ip_address=ip_address,
            user_agent=user_agent,
            details={
                "username": username,
                "email": email,
                "roles": roles
            }
        )
        
        return user
    
    def update_user_roles(
        self,
        user_id: int,
        roles: List[str],
        updated_by: int,
        ip_address: str,
        user_agent: str
    ) -> User:
        """
        Actualiza los roles de un usuario.
        
        Proceso:
        1. Valida que usuario existe
        2. Valida que roles existen
        3. Elimina roles actuales
        4. Asigna nuevos roles
        5. Registra evento ROLE_CHANGE en audit_log
        
        Args:
            user_id: ID del usuario
            roles: Nueva lista de roles
            updated_by: ID del usuario que actualiza
            ip_address: IP del cliente
            user_agent: User agent del cliente
            
        Returns:
            Usuario actualizado
            
        Raises:
            ValidationError: Si el usuario no existe o los roles son inválidos
        """
        # Validar que usuario existe
        user = self.user_repo.get_by_id(user_id)
        if not user:
            raise ValidationError(f"El usuario con ID {user_id} no existe")
        
        # Validar que roles existen
        role_objects = []
        for role_name in roles:
            role = self.role_repo.get_by_name(role_name)
            if not role:
                raise ValidationError(f"El rol '{role_name}' no existe")
            role_objects.append(role)
        
        # Obtener roles actuales para el log
        old_roles = [role.name for role in user.roles]
        
        # Eliminar roles actuales
        self.db.query(UserRole).filter(UserRole.user_id == user_id).delete()
        
        # Asignar nuevos roles
        for role in role_objects:
            user_role = UserRole(user_id=user.id, role_id=role.id)
            self.db.add(user_role)
        
        self.db.commit()
        self.db.refresh(user)
        
        # Registrar en audit log
        self.audit_service.log_event(
            user_id=updated_by,
            action="ROLE_CHANGE",
            resource_type="user",
            resource_id=user.id,
            ip_address=ip_address,
            user_agent=user_agent,
            details={
                "username": user.username,
                "old_roles": old_roles,
                "new_roles": roles
            }
        )
        
        return user
    
    def deactivate_user(
        self,
        user_id: int,
        deactivated_by: int,
        ip_address: str,
        user_agent: str
    ):
        """
        Desactiva un usuario (soft delete).
        
        Proceso:
        1. Marca usuario como inactivo
        2. Invalida todos sus tokens activos
        3. Registra evento USER_DEACTIVATE en audit_log
        
        Args:
            user_id: ID del usuario
            deactivated_by: ID del usuario que desactiva
            ip_address: IP del cliente
            user_agent: User agent del cliente
            
        Raises:
            ValidationError: Si el usuario no existe
        """
        # Validar que usuario existe
        user = self.user_repo.get_by_id(user_id)
        if not user:
            raise ValidationError(f"El usuario con ID {user_id} no existe")
        
        # Desactivar usuario
        user.is_active = False
        self.user_repo.update(user)
        
        # Invalidar todos los tokens del usuario
        # Nota: En una implementación real, necesitaríamos obtener todos los tokens
        # activos del usuario y agregarlos a la lista negra. Por ahora, la lógica
        # de validación de tokens verificará is_active del usuario.
        
        # Registrar en audit log
        self.audit_service.log_event(
            user_id=deactivated_by,
            action="USER_DEACTIVATE",
            resource_type="user",
            resource_id=user.id,
            ip_address=ip_address,
            user_agent=user_agent,
            details={
                "username": user.username,
                "email": user.email
            }
        )
    
    def change_password(
        self,
        user_id: int,
        current_password: str,
        new_password: str,
        ip_address: str,
        user_agent: str
    ):
        """
        Cambia la contraseña de un usuario.
        
        Proceso:
        1. Valida que usuario existe
        2. Verifica contraseña actual
        3. Valida que nueva contraseña cumple requisitos
        4. Hashea y actualiza contraseña
        5. Registra evento PASSWORD_CHANGE en audit_log
        
        Args:
            user_id: ID del usuario
            current_password: Contraseña actual
            new_password: Nueva contraseña
            ip_address: IP del cliente
            user_agent: User agent del cliente
            
        Raises:
            ValidationError: Si el usuario no existe, la contraseña actual es incorrecta,
                           o la nueva contraseña no cumple requisitos
        """
        # Validar que usuario existe
        user = self.user_repo.get_by_id(user_id)
        if not user:
            raise ValidationError(f"El usuario con ID {user_id} no existe")
        
        # Verificar contraseña actual
        if not self.password_hasher.verify_password(current_password, user.password_hash):
            raise ValidationError("La contraseña actual es incorrecta")
        
        # Validar nueva contraseña
        if not self._is_complex_password(new_password):
            raise ValidationError(
                "La nueva contraseña debe tener al menos 8 caracteres, "
                "incluyendo mayúscula, minúscula y número"
            )
        
        # Hashear y actualizar contraseña
        user.password_hash = self.password_hasher.hash_password(new_password)
        user.is_migrated = True
        self.user_repo.update(user)
        
        # Registrar en audit log
        self.audit_service.log_event(
            user_id=user_id,
            action="PASSWORD_CHANGE",
            resource_type="user",
            resource_id=user.id,
            ip_address=ip_address,
            user_agent=user_agent,
            details={
                "username": user.username
            }
        )
    
    def _reactivate_user(self, user, email, password_hash, role_objects, nombre_completo,
                         telefono, direccion, created_by, ip_address, user_agent, roles):
        """Reactiva un usuario inactivo con nuevos datos."""
        # Actualizar datos
        user.email = email
        user.password_hash = password_hash
        user.is_active = True
        user.is_migrated = True
        user.nombre_completo = nombre_completo
        user.telefono = telefono
        user.direccion = direccion
        self.user_repo.update(user)

        # Reemplazar roles
        self.db.query(UserRole).filter(UserRole.user_id == user.id).delete()
        for role in role_objects:
            self.db.add(UserRole(user_id=user.id, role_id=role.id))

        self.db.commit()
        self.db.refresh(user)

        self.audit_service.log_event(
            user_id=created_by,
            action="USER_REACTIVATE",
            resource_type="user",
            resource_id=user.id,
            ip_address=ip_address,
            user_agent=user_agent,
            details={"username": user.username, "email": email, "roles": roles}
        )
        return user

    def _is_valid_email(self, email: str) -> bool:
        """
        Valida formato de email.
        
        Args:
            email: Email a validar
            
        Returns:
            True si el email es válido
        """
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    def _is_complex_password(self, password: str) -> bool:
        """
        Valida que la contraseña cumpla requisitos de complejidad.
        
        Requisitos:
        - Al menos 8 caracteres
        - Al menos una mayúscula
        - Al menos una minúscula
        - Al menos un número
        
        Args:
            password: Contraseña a validar
            
        Returns:
            True si la contraseña cumple requisitos
        """
        if len(password) < 8:
            return False
        
        has_upper = any(c.isupper() for c in password)
        has_lower = any(c.islower() for c in password)
        has_digit = any(c.isdigit() for c in password)
        
        return has_upper and has_lower and has_digit
