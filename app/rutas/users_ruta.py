"""
Endpoints de gestión de usuarios.

Implementa operaciones CRUD para usuarios con control de acceso basado en roles.
"""

import os
from typing import Optional
from fastapi import APIRouter, Request, HTTPException, status, Depends, Query
from sqlalchemy.orm import Session

from app.configuracion.base_datos import obtener_db
from app.configuracion.limiter import limiter
from app.esquemas.user_schema import (
    CreateUserRequest,
    UpdateUserRequest,
    ChangePasswordRequest,
    UserResponse,
    UsersListResponse
)
from app.servicios.user_service import UserService, ValidationError, DuplicateError
from app.repositorios.user_repository import UserRepository
from app.repositorios.role_repository import RoleRepository
from app.repositorios.token_blacklist_repository import TokenBlacklistRepository
from app.servicios.audit_service import AuditService
from app.repositorios.audit_log_repository import AuditLogRepository
from app.seguridad.password_hasher import PasswordHasher
from app.seguridad.auth_middleware import require_auth, require_role


router = APIRouter(prefix="/users", tags=["Users"])


def get_user_service(db: Session = Depends(obtener_db)) -> UserService:
    """Dependency para obtener UserService."""
    user_repo = UserRepository(db)
    role_repo = RoleRepository(db)
    token_blacklist_repo = TokenBlacklistRepository(db)
    password_hasher = PasswordHasher()
    audit_log_repo = AuditLogRepository(db)
    audit_service = AuditService(audit_log_repo)
    
    return UserService(
        user_repo=user_repo,
        role_repo=role_repo,
        token_blacklist_repo=token_blacklist_repo,
        password_hasher=password_hasher,
        audit_service=audit_service,
        db=db
    )



@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
@require_role("ADMIN")
@limiter.limit(f"{os.getenv('RATE_LIMIT_CREATE_PER_MINUTE', '30')}/minute")
async def create_user(
    request: Request,
    user_data: CreateUserRequest,
    db: Session = Depends(obtener_db),
    user_service: UserService = Depends(get_user_service)
):
    """
    Crea un nuevo usuario (requiere rol ADMIN).
    
    Rate limit: 30 requests/minuto por usuario autenticado (configurable con RATE_LIMIT_CREATE_PER_MINUTE).
    
    Validaciones:
    - Username único
    - Email válido y único
    - Contraseña cumple requisitos de complejidad
    - Roles existen en el sistema
    """
    try:
        # Obtener información del request
        current_user = request.state.user
        ip_address = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "unknown")
        
        # Crear usuario
        user = user_service.create_user(
            username=user_data.username,
            email=user_data.email,
            password=user_data.password,
            roles=user_data.roles,
            created_by=current_user.id,
            ip_address=ip_address,
            user_agent=user_agent,
            nombre_completo=user_data.nombre_completo,
            telefono=user_data.telefono,
            direccion=user_data.direccion
        )
        
        # Construir response
        return UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            roles=[role.name for role in user.roles],
            is_active=user.is_active,
            created_at=user.created_at,
            nombre_completo=user.nombre_completo,
            telefono=user.telefono,
            direccion=user.direccion
        )
        
    except DuplicateError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )



@router.get("", response_model=UsersListResponse)
@require_role("ADMIN")
@limiter.limit(f"{os.getenv('RATE_LIMIT_READ_PER_MINUTE', '100')}/minute")
async def get_users(
    request: Request,
    skip: int = Query(0, ge=0, description="Número de registros a saltar"),
    limit: int = Query(100, ge=1, le=1000, description="Número máximo de registros"),
    db: Session = Depends(obtener_db)
):
    """
    Lista todos los usuarios con paginación (requiere rol ADMIN).
    
    Rate limit: 100 requests/minuto por usuario autenticado (configurable con RATE_LIMIT_READ_PER_MINUTE).
    
    Soporta paginación mediante query params skip y limit.
    """
    from app.modelos.user import User
    
    user_repo = UserRepository(db)
    
    # Obtener usuarios con paginación
    users = user_repo.get_all(skip=skip, limit=limit, include_inactive=False)
    
    # Contar total de usuarios activos
    total = db.query(User).filter_by(is_active=True).count()
    
    # Construir response
    users_response = [
        UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            roles=[role.name for role in user.roles],
            is_active=user.is_active,
            created_at=user.created_at,
            nombre_completo=user.nombre_completo,
            telefono=user.telefono,
            direccion=user.direccion
        )
        for user in users
    ]
    
    return UsersListResponse(users=users_response, total=total)



@router.get("/{user_id}", response_model=UserResponse)
@require_auth
@limiter.limit(f"{os.getenv('RATE_LIMIT_READ_PER_MINUTE', '100')}/minute")
async def get_user(
    request: Request,
    user_id: int,
    db: Session = Depends(obtener_db)
):
    """
    Obtiene un usuario por ID.
    
    Rate limit: 100 requests/minuto por usuario autenticado (configurable con RATE_LIMIT_READ_PER_MINUTE).
    
    Permisos:
    - Usuarios pueden ver su propio perfil
    - ADMIN puede ver cualquier usuario
    """
    current_user = request.state.user
    user_roles = [role.name for role in current_user.roles]
    
    # Verificar permisos: usuario puede ver su propio perfil o ser ADMIN
    if current_user.id != user_id and "ADMIN" not in user_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para ver este usuario"
        )
    
    # Obtener usuario
    user_repo = UserRepository(db)
    user = user_repo.get_by_id(user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Usuario con ID {user_id} no encontrado"
        )
    
    # Construir response
    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        roles=[role.name for role in user.roles],
        is_active=user.is_active,
        created_at=user.created_at,
        nombre_completo=user.nombre_completo,
        telefono=user.telefono,
        direccion=user.direccion
    )



@router.patch("/{user_id}", response_model=UserResponse)
@require_role("ADMIN")
async def update_user(
    request: Request,
    user_id: int,
    user_data: UpdateUserRequest,
    db: Session = Depends(obtener_db),
    user_service: UserService = Depends(get_user_service)
):
    """
    Actualiza un usuario (requiere rol ADMIN).
    
    Permite actualizar email y roles. Si se cambian roles, se registra en auditoría.
    """
    try:
        # Obtener información del request
        current_user = request.state.user
        ip_address = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "unknown")
        
        # Obtener usuario
        user_repo = UserRepository(db)
        user = user_repo.get_by_id(user_id)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Usuario con ID {user_id} no encontrado"
            )
        
        # Actualizar email si se proporciona
        if user_data.email is not None:
            # Verificar que el email no esté en uso por otro usuario
            existing_user = user_repo.get_by_email(user_data.email)
            if existing_user and existing_user.id != user_id:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"El email '{user_data.email}' ya está en uso"
                )
            user.email = user_data.email
            user_repo.update(user)
        
        # Actualizar roles si se proporcionan
        if user_data.roles is not None:
            user = user_service.update_user_roles(
                user_id=user_id,
                roles=user_data.roles,
                updated_by=current_user.id,
                ip_address=ip_address,
                user_agent=user_agent
            )
        
        # Refrescar usuario para obtener datos actualizados
        db.refresh(user)
        
        # Construir response
        return UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            roles=[role.name for role in user.roles],
            is_active=user.is_active,
            created_at=user.created_at,
            nombre_completo=user.nombre_completo,
            telefono=user.telefono,
            direccion=user.direccion
        )
        
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )



@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
@require_role("ADMIN")
async def delete_user(
    request: Request,
    user_id: int,
    db: Session = Depends(obtener_db),
    user_service: UserService = Depends(get_user_service)
):
    """
    Desactiva un usuario - soft delete (requiere rol ADMIN).
    
    Marca el usuario como inactivo en lugar de eliminarlo de la base de datos.
    """
    try:
        # Obtener información del request
        current_user = request.state.user
        ip_address = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "unknown")
        
        # Verificar que el usuario existe
        user_repo = UserRepository(db)
        user = user_repo.get_by_id(user_id)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Usuario con ID {user_id} no encontrado"
            )
        
        # Desactivar usuario
        user_service.deactivate_user(
            user_id=user_id,
            deactivated_by=current_user.id,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        return None
        
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )



@router.post("/me/change-password", status_code=status.HTTP_200_OK)
@require_auth
async def change_password(
    request: Request,
    password_data: ChangePasswordRequest,
    db: Session = Depends(obtener_db),
    user_service: UserService = Depends(get_user_service)
):
    """
    Cambia la contraseña del usuario autenticado.
    
    Requiere autenticación. Valida la contraseña actual antes de cambiarla.
    """
    try:
        # Obtener información del request
        current_user = request.state.user
        ip_address = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "unknown")
        
        # Cambiar contraseña
        user_service.change_password(
            user_id=current_user.id,
            current_password=password_data.current_password,
            new_password=password_data.new_password,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        return {"message": "Contraseña actualizada exitosamente"}
        
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
