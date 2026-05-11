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
    description="""
    Create a new user account with specified roles.

    **Authentication Required:** Yes (Bearer token)
    **Required Role:** ADMIN

    **Validation:**
    - Username must be unique and alphanumeric (3-50 chars)
    - Email must be valid and unique
    - Password must meet complexity requirements (8+ chars, uppercase, lowercase, number)
    - Roles must exist in the system

    **Available Roles:**
    - ADMIN: Full system access
    - MECANICO: Mechanic - can manage tickets and processes
    - RECEPCIONISTA: Receptionist - can create tickets and view data
    - SOLO_LECTURA: Read-only access

    **Audit:**
    - USER_CREATED event logged with creator ID, IP, and user agent

    **Rate Limiting:**
    - 30 requests per minute per authenticated user
    """,
    responses={
        201: {
            "description": "User created successfully",
            "content": {
                "application/json": {
                    "example": {
                        "id": 5,
                        "username": "mechanic1",
                        "email": "mechanic1@taller.com",
                        "roles": ["MECANICO"],
                        "is_active": True,
                        "created_at": "2026-04-06T10:30:00",
                        "nombre_completo": "Carlos Méndez",
                        "telefono": "3001234567",
                        "direccion": "Calle 123 #45-67",
                    }
                }
            },
        },
        400: {
            "description": "Validation error",
            "content": {
                "application/json": {
                    "example": {
                        "error": "validation_error",
                        "message": "Password must contain at least one uppercase letter",
                    }
                }
            },
        },
        403: {
            "description": "Insufficient permissions",
            "content": {
                "application/json": {
                    "example": {
                        "error": "insufficient_permissions",
                        "message": "ADMIN role required",
                    }
                }
            },
        },
        409: {
            "description": "Duplicate username or email",
            "content": {
                "application/json": {
                    "example": {
                        "error": "duplicate_resource",
                        "message": "Username 'mechanic1' already exists",
                    }
                }
            },
        },
    },
)
@require_role("ADMIN")
@limiter.limit(f"{os.getenv('RATE_LIMIT_CREATE_PER_MINUTE', '30')}/minute")
async def create_user(
    request: Request,
    user_data: CreateUserRequest,
    db: Session = Depends(obtener_db),
    user_service: UserService = Depends(get_user_service),
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
            direccion=user_data.direccion,
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
    """
    Lista usuarios activos del taller con solo los campos necesarios para asignación.

    Accesible para ADMIN, MECANICO y RECEPCIONISTA — no expone datos sensibles.
    Filtra por taller_id del JWT (aislamiento multi-tenant).
    """
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
    description="""
    Retrieve a paginated list of all active users in the system.

    **Authentication Required:** Yes (Bearer token)
    **Required Role:** ADMIN

    **Pagination:**
    - Default: skip=0, limit=100
    - Maximum limit: 1000 users per request
    - Only active users are returned (is_active=true)

    **Response:**
    - users: Array of user objects with roles
    - total: Total count of active users

    **Use Case:**
    - User management dashboard
    - Role assignment interface
    - System administration

    **Rate Limiting:**
    - 100 requests per minute per authenticated user
    """,
    responses={
        200: {
            "description": "List of users with total count",
            "content": {
                "application/json": {
                    "example": {
                        "users": [
                            {
                                "id": 1,
                                "username": "admin",
                                "email": "admin@taller.com",
                                "roles": ["ADMIN"],
                                "is_active": True,
                                "created_at": "2026-01-01T00:00:00",
                            },
                            {
                                "id": 2,
                                "username": "mechanic1",
                                "email": "mechanic1@taller.com",
                                "roles": ["MECANICO"],
                                "is_active": True,
                                "created_at": "2026-02-15T10:30:00",
                            },
                        ],
                        "total": 2,
                    }
                }
            },
        },
        403: {
            "description": "Insufficient permissions",
            "content": {
                "application/json": {
                    "example": {
                        "error": "insufficient_permissions",
                        "message": "ADMIN role required",
                    }
                }
            },
        },
    },
)
@require_role("ADMIN")
@limiter.limit(f"{os.getenv('RATE_LIMIT_READ_PER_MINUTE', '100')}/minute")
async def get_users(
    request: Request,
    skip: int = Query(0, ge=0, description="Número de registros a saltar"),
    limit: int = Query(100, ge=1, le=1000, description="Número máximo de registros"),
    db: Session = Depends(obtener_db),
):
    """
    Lista todos los usuarios con paginación (requiere rol ADMIN).

    Rate limit: 100 requests/minuto por usuario autenticado (configurable con RATE_LIMIT_READ_PER_MINUTE).

    Soporta paginación mediante query params skip y limit.
    """
    from app.modelos.user import User

    user_repo = UserRepository(db)

    # Filtrar por taller del usuario autenticado — aislamiento multi-tenant
    taller_id = request.state.taller_id

    # Obtener usuarios con paginación
    users = user_repo.get_all(skip=skip, limit=limit, include_inactive=False, taller_id=taller_id)

    # Contar total de usuarios activos del mismo taller
    total = db.query(User).filter(User.is_active == True, User.taller_id == taller_id).count()

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
            direccion=user.direccion,
        )
        for user in users
    ]

    return UsersListResponse(users=users_response, total=total)


@router.get("/{user_id}", response_model=UserResponse)
@require_auth
@limiter.limit(f"{os.getenv('RATE_LIMIT_READ_PER_MINUTE', '100')}/minute")
async def get_user(request: Request, user_id: int, db: Session = Depends(obtener_db)):
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
            status_code=status.HTTP_403_FORBIDDEN, detail="No tienes permiso para ver este usuario"
        )

    # Obtener usuario
    user_repo = UserRepository(db)
    user = user_repo.get_by_id(user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Usuario con ID {user_id} no encontrado"
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
                detail=f"Usuario con ID {user_id} no encontrado",
            )

        # Actualizar email si se proporciona
        if user_data.email is not None:
            # Verificar que el email no esté en uso por otro usuario
            existing_user = user_repo.get_by_email(user_data.email)
            if existing_user and existing_user.id != user_id:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"El email '{user_data.email}' ya está en uso",
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
                user_agent=user_agent,
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
                detail=f"Usuario con ID {user_id} no encontrado",
            )

        # Desactivar usuario
        user_service.deactivate_user(
            user_id=user_id,
            deactivated_by=current_user.id,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        return None

    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/me/change-password", status_code=status.HTTP_200_OK)
@require_auth
async def change_password(
    request: Request,
    password_data: ChangePasswordRequest,
    db: Session = Depends(obtener_db),
    user_service: UserService = Depends(get_user_service),
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
            user_agent=user_agent,
        )

        return {"message": "Contraseña actualizada exitosamente"}

    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
