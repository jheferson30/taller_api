"""
Endpoints de gestión de usuarios.

Implementa operaciones CRUD para usuarios con control de acceso basado en roles.
"""

import os

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.configuracion.base_datos import obtener_db
from app.configuracion.limiter import limiter
from app.esquemas.user_schema import (
    ChangePasswordRequest,
    CreateUserRequest,
    UpdateProfileRequest,
    UpdateUserRequest,
    UserResponse,
    UsersListResponse,
)
from app.repositorios.audit_log_repository import AuditLogRepository
from app.repositorios.role_repository import RoleRepository
from app.repositorios.token_blacklist_repository import TokenBlacklistRepository
from app.repositorios.user_repository import UserRepository
from app.seguridad.auth_middleware import require_auth, require_role
from app.seguridad.password_hasher import PasswordHasher
from app.servicios.audit_service import AuditService
from app.servicios.user_service import DuplicateError, UserService, ValidationError

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
        db=db,
    )


@router.post(
    "",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create new user",
)
@require_role("ADMIN")
@limiter.limit(f"{os.getenv('RATE_LIMIT_CREATE_PER_MINUTE', '30')}/minute")
async def create_user(
    request: Request,
    user_data: CreateUserRequest,
    db: Session = Depends(obtener_db),
    user_service: UserService = Depends(get_user_service),
):
    """Crea un nuevo usuario (requiere rol ADMIN)."""
    try:
        current_user = request.state.user
        ip_address = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "unknown")

        user = user_service.create_user(
            username=user_data.username,
            email=user_data.email,
            password=user_data.password,
            roles=user_data.roles,
            taller_id=request.state.taller_id,
            created_by=current_user.id,
            ip_address=ip_address,
            user_agent=user_agent,
            nombre_completo=user_data.nombre_completo,
            telefono=user_data.telefono,
            direccion=user_data.direccion,
        )

        return UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            roles=[role.name for role in user.roles],
            is_active=user.is_active,
            created_at=user.created_at,
            nombre_completo=user.nombre_completo,
            telefono=user.telefono,
            direccion=user.direccion,
        )

    except DuplicateError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get(
    "/para-asignacion",
    summary="Lista usuarios del taller para asignación de tickets",
    description="Retorna id y nombre de los usuarios activos del taller. Accesible para todos los roles del taller.",
)
@require_auth
@limiter.limit(f"{os.getenv('RATE_LIMIT_READ_PER_MINUTE', '100')}/minute")
async def get_users_para_asignacion(
    request: Request,
    db: Session = Depends(obtener_db),
):
    """Lista usuarios activos del taller para asignación de tickets."""
    from app.modelos.user import User

    taller_id = request.state.taller_id
    users = (
        db.query(User)
        .filter(User.taller_id == taller_id, User.is_active == True)
        .order_by(User.nombre_completo, User.username)
        .all()
    )
    return {
        "users": [
            {
                "id": u.id,
                "username": u.username,
                "nombre_completo": u.nombre_completo or u.username,
            }
            for u in users
        ]
    }


@router.get(
    "",
    response_model=UsersListResponse,
    summary="List all users with pagination",
)
@require_role("ADMIN")
@limiter.limit(f"{os.getenv('RATE_LIMIT_READ_PER_MINUTE', '100')}/minute")
async def get_users(
    request: Request,
    skip: int = Query(0, ge=0, description="Número de registros a saltar"),
    limit: int = Query(100, ge=1, le=1000, description="Número máximo de registros"),
    db: Session = Depends(obtener_db),
):
    """Lista todos los usuarios con paginación (requiere rol ADMIN)."""
    from app.modelos.user import User

    user_repo = UserRepository(db)
    taller_id = request.state.taller_id

    users = user_repo.get_all(skip=skip, limit=limit, include_inactive=False, taller_id=taller_id)
    total = db.query(User).filter(User.is_active == True, User.taller_id == taller_id).count()

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
            direccion=user.direccion,
        )
        for user in users
    ]

    return UsersListResponse(users=users_response, total=total)


# ── Endpoints /me — DEBEN ir ANTES de /{user_id} para evitar conflicto de rutas ──


@router.patch("/me", response_model=UserResponse, status_code=status.HTTP_200_OK)
@require_auth
async def update_my_profile(
    request: Request,
    profile_data: UpdateProfileRequest,
    db: Session = Depends(obtener_db),
):
    """
    Actualiza el perfil del usuario autenticado.

    Permite cambiar nombre completo, teléfono, dirección y email.
    """
    # request.state.user viene de la sesión del middleware — no es persistente
    # en la sesión del endpoint. Recargamos desde la sesión del endpoint.
    user_id = request.state.user.id
    user_repo = UserRepository(db)
    user = user_repo.get_by_id(user_id)

    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    updates = profile_data.model_dump(exclude_unset=True)

    if not updates:
        raise HTTPException(status_code=400, detail="No se enviaron campos para actualizar")

    if "email" in updates and updates["email"] != user.email:
        existing = user_repo.get_by_email(updates["email"])
        if existing and existing.id != user.id:
            raise HTTPException(status_code=409, detail="El email ya está en uso")

    for campo, valor in updates.items():
        setattr(user, campo, valor)

    user_repo.update(user)

    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        roles=[role.name for role in user.roles],
        is_active=user.is_active,
        created_at=user.created_at,
        nombre_completo=user.nombre_completo,
        telefono=user.telefono,
        direccion=user.direccion,
    )


@router.post("/me/change-password", status_code=status.HTTP_200_OK)
@require_auth
async def change_password(
    request: Request,
    password_data: ChangePasswordRequest,
    db: Session = Depends(obtener_db),
    user_service: UserService = Depends(get_user_service),
):
    """Cambia la contraseña del usuario autenticado."""
    try:
        current_user = request.state.user
        ip_address = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "unknown")

        user_service.change_password(
            user_id=current_user.id,
            current_password=password_data.current_password,
            new_password=password_data.new_password,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        return {"message": "Contraseña actualizada exitosamente"}

    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ── Endpoints /{user_id} — van DESPUÉS de /me ──


@router.get("/{user_id}", response_model=UserResponse)
@require_auth
@limiter.limit(f"{os.getenv('RATE_LIMIT_READ_PER_MINUTE', '100')}/minute")
async def get_user(request: Request, user_id: int, db: Session = Depends(obtener_db)):
    """Obtiene un usuario por ID."""
    current_user = request.state.user
    user_roles = [role.name for role in current_user.roles]

    if current_user.id != user_id and "ADMIN" not in user_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="No tienes permiso para ver este usuario"
        )

    user_repo = UserRepository(db)
    user = user_repo.get_by_id(user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Usuario con ID {user_id} no encontrado"
        )

    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        roles=[role.name for role in user.roles],
        is_active=user.is_active,
        created_at=user.created_at,
        nombre_completo=user.nombre_completo,
        telefono=user.telefono,
        direccion=user.direccion,
    )


@router.patch("/{user_id}", response_model=UserResponse)
@require_role("ADMIN")
async def update_user(
    request: Request,
    user_id: int,
    user_data: UpdateUserRequest,
    db: Session = Depends(obtener_db),
    user_service: UserService = Depends(get_user_service),
):
    """Actualiza email y roles de un usuario (requiere rol ADMIN)."""
    try:
        current_user = request.state.user
        ip_address = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "unknown")

        user_repo = UserRepository(db)
        user = user_repo.get_by_id(user_id)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Usuario con ID {user_id} no encontrado",
            )

        if user_data.email is not None:
            existing_user = user_repo.get_by_email(user_data.email)
            if existing_user and existing_user.id != user_id:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"El email '{user_data.email}' ya está en uso",
                )
            user.email = user_data.email
            user_repo.update(user)

        if user_data.roles is not None:
            user = user_service.update_user_roles(
                user_id=user_id,
                roles=user_data.roles,
                updated_by=current_user.id,
                ip_address=ip_address,
                user_agent=user_agent,
            )

        db.refresh(user)

        return UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            roles=[role.name for role in user.roles],
            is_active=user.is_active,
            created_at=user.created_at,
            nombre_completo=user.nombre_completo,
            telefono=user.telefono,
            direccion=user.direccion,
        )

    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
@require_role("ADMIN")
async def delete_user(
    request: Request,
    user_id: int,
    db: Session = Depends(obtener_db),
    user_service: UserService = Depends(get_user_service),
):
    """Desactiva un usuario — soft delete (requiere rol ADMIN)."""
    try:
        current_user = request.state.user
        ip_address = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "unknown")

        user_repo = UserRepository(db)
        user = user_repo.get_by_id(user_id)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Usuario con ID {user_id} no encontrado",
            )

        user_service.deactivate_user(
            user_id=user_id,
            deactivated_by=current_user.id,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        return None

    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
