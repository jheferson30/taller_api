"""
Esquemas Pydantic para endpoints de usuarios.

Define los modelos de request/response para la API de gestión de usuarios.
"""

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, validator


class CreateUserRequest(BaseModel):
    """Request para crear un nuevo usuario."""

    username: str = Field(..., min_length=3, max_length=50, description="Nombre de usuario único")
    email: EmailStr = Field(..., description="Email del usuario")
    password: str = Field(..., min_length=8, description="Contraseña (mínimo 8 caracteres)")
    roles: list[str] = Field(..., min_items=1, description="Lista de roles del usuario")
    nombre_completo: str | None = Field(
        None, max_length=150, description="Nombre completo del empleado"
    )
    telefono: str | None = Field(None, max_length=20, description="Teléfono del empleado")
    direccion: str | None = Field(None, max_length=255, description="Dirección del empleado")

    @validator("username")
    def validate_username(cls, v):
        """Valida que el username solo contenga caracteres alfanuméricos y guiones."""
        if not v.replace("_", "").replace("-", "").isalnum():
            raise ValueError(
                "El username solo puede contener letras, números, guiones y guiones bajos"
            )
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "username": "mechanic1",
                "email": "mechanic1@taller.com",
                "password": "SecurePass123!",
                "roles": ["MECANICO"],
                "nombre_completo": "Carlos Méndez",
                "telefono": "3001234567",
                "direccion": "Calle 123 #45-67",
            }
        }


class UpdateUserRequest(BaseModel):
    """Request para actualizar un usuario (solo ADMIN)."""

    email: EmailStr | None = Field(None, description="Nuevo email del usuario")
    roles: list[str] | None = Field(None, min_items=1, description="Nueva lista de roles")

    class Config:
        json_schema_extra = {
            "example": {"email": "newemail@taller.com", "roles": ["MECANICO", "RECEPCIONISTA"]}
        }


class UpdateProfileRequest(BaseModel):
    """Request para que el usuario actualice su propio perfil."""

    nombre_completo: str | None = Field(None, max_length=150, description="Nombre completo")
    telefono: str | None = Field(None, max_length=20, description="Teléfono")
    direccion: str | None = Field(None, max_length=255, description="Dirección")
    email: EmailStr | None = Field(None, description="Email")

    class Config:
        json_schema_extra = {
            "example": {
                "nombre_completo": "Juan Pérez",
                "telefono": "3001234567",
                "direccion": "Calle 10 #5-20",
                "email": "juan@gmail.com",
            }
        }


class ChangePasswordRequest(BaseModel):
    """Request para cambiar contraseña."""

    current_password: str = Field(..., description="Contraseña actual")
    new_password: str = Field(
        ..., min_length=8, description="Nueva contraseña (mínimo 8 caracteres)"
    )

    class Config:
        json_schema_extra = {
            "example": {"current_password": "OldPass123!", "new_password": "NewSecurePass456!"}
        }


class UserResponse(BaseModel):
    """Response con datos de un usuario."""

    id: int
    username: str
    email: str
    roles: list[str]
    is_active: bool
    created_at: datetime
    nombre_completo: str | None = None
    telefono: str | None = None
    direccion: str | None = None

    class Config:
        from_attributes = True


class UsersListResponse(BaseModel):
    """Response con lista de usuarios y total."""

    users: list[UserResponse]
    total: int
