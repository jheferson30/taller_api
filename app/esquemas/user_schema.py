"""
Esquemas Pydantic para endpoints de usuarios.

Define los modelos de request/response para la API de gestión de usuarios.
"""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, EmailStr, Field, validator


class CreateUserRequest(BaseModel):
    """Request para crear un nuevo usuario."""
    username: str = Field(..., min_length=3, max_length=50, description="Nombre de usuario único")
    email: EmailStr = Field(..., description="Email del usuario")
    password: str = Field(..., min_length=8, description="Contraseña (mínimo 8 caracteres)")
    roles: List[str] = Field(..., min_items=1, description="Lista de roles del usuario")
    nombre_completo: Optional[str] = Field(None, max_length=150, description="Nombre completo del empleado")
    telefono: Optional[str] = Field(None, max_length=20, description="Teléfono del empleado")
    direccion: Optional[str] = Field(None, max_length=255, description="Dirección del empleado")
    
    @validator('username')
    def validate_username(cls, v):
        """Valida que el username solo contenga caracteres alfanuméricos y guiones."""
        if not v.replace('_', '').replace('-', '').isalnum():
            raise ValueError('El username solo puede contener letras, números, guiones y guiones bajos')
        return v


class UpdateUserRequest(BaseModel):
    """Request para actualizar un usuario."""
    email: Optional[EmailStr] = Field(None, description="Nuevo email del usuario")
    roles: Optional[List[str]] = Field(None, min_items=1, description="Nueva lista de roles")


class ChangePasswordRequest(BaseModel):
    """Request para cambiar contraseña."""
    current_password: str = Field(..., description="Contraseña actual")
    new_password: str = Field(..., min_length=8, description="Nueva contraseña (mínimo 8 caracteres)")


class UserResponse(BaseModel):
    """Response con datos de un usuario."""
    id: int
    username: str
    email: str
    roles: List[str]
    is_active: bool
    created_at: datetime
    nombre_completo: Optional[str] = None
    telefono: Optional[str] = None
    direccion: Optional[str] = None
    
    class Config:
        from_attributes = True


class UsersListResponse(BaseModel):
    """Response con lista de usuarios y total."""
    users: List[UserResponse]
    total: int
