"""
Esquemas Pydantic para endpoints de autenticación.

Define los modelos de request/response para login, refresh, logout,
forgot password y reset password.
"""

from typing import List, Optional
from pydantic import BaseModel, Field, validator


class LoginRequest(BaseModel):
    """Request para login de usuario."""
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=1)


class UserResponse(BaseModel):
    """Información del usuario en respuesta de login."""
    id: int
    username: str
    email: str
    roles: List[str]


class LoginResponse(BaseModel):
    """Response de login exitoso con tokens y datos del usuario."""
    access_token: str
    refresh_token: str
    user: UserResponse


class RefreshRequest(BaseModel):
    """Request para refrescar access token."""
    refresh_token: str = Field(..., min_length=1)


class RefreshResponse(BaseModel):
    """Response con nuevo access token."""
    access_token: str


class LogoutRequest(BaseModel):
    """Request para logout (invalidar refresh token)."""
    refresh_token: str = Field(..., min_length=1)


class ForgotPasswordRequest(BaseModel):
    """Request para solicitar recuperación de contraseña."""
    email: str = Field(..., min_length=3, max_length=100)
    
    @validator('email')
    def validate_email_format(cls, v):
        """Valida formato básico de email."""
        if '@' not in v or '.' not in v.split('@')[-1]:
            raise ValueError('Formato de email inválido')
        return v.lower()


class ForgotPasswordResponse(BaseModel):
    """Response genérico para forgot password (no revela si email existe)."""
    message: str


class ResetPasswordRequest(BaseModel):
    """Request para resetear contraseña con token."""
    token: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8, max_length=100)
    
    @validator('new_password')
    def validate_password_complexity(cls, v):
        """
        Valida complejidad de contraseña:
        - Mínimo 8 caracteres
        - Al menos una mayúscula
        - Al menos una minúscula
        - Al menos un número
        """
        if len(v) < 8:
            raise ValueError('La contraseña debe tener al menos 8 caracteres')
        
        if not any(c.isupper() for c in v):
            raise ValueError('La contraseña debe contener al menos una letra mayúscula')
        
        if not any(c.islower() for c in v):
            raise ValueError('La contraseña debe contener al menos una letra minúscula')
        
        if not any(c.isdigit() for c in v):
            raise ValueError('La contraseña debe contener al menos un número')
        
        return v


class ResetPasswordResponse(BaseModel):
    """Response de reset password exitoso."""
    message: str
