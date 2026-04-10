"""
Esquemas Pydantic para endpoints de autenticación.

Define los modelos de request/response para login, refresh, logout,
forgot password y reset password.
"""

from pydantic import BaseModel, Field, validator


class LoginRequest(BaseModel):
    """Request para login de usuario."""

    username: str = Field(..., min_length=3, max_length=50, description="Username del usuario")
    password: str = Field(..., min_length=1, description="Contraseña del usuario")

    class Config:
        json_schema_extra = {"example": {"username": "admin", "password": "SecurePass123!"}}


class UserResponse(BaseModel):
    """Información del usuario en respuesta de login."""

    id: int = Field(..., description="ID único del usuario")
    username: str = Field(..., description="Nombre de usuario")
    email: str = Field(..., description="Email del usuario")
    roles: list[str] = Field(..., description="Lista de roles asignados")

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "username": "admin",
                "email": "admin@taller.com",
                "roles": ["ADMIN"],
            }
        }


class LoginResponse(BaseModel):
    """Response de login exitoso con tokens y datos del usuario."""

    access_token: str = Field(..., description="JWT access token (15 min expiry)")
    refresh_token: str = Field(..., description="JWT refresh token (7 days expiry)")
    user: UserResponse = Field(..., description="Datos del usuario autenticado")

    class Config:
        json_schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIiwicm9sZXMiOlsiQURNSU4iXSwiZXhwIjoxNzE0OTk5OTk5fQ.signature",
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIiwidHlwZSI6InJlZnJlc2giLCJleHAiOjE3MTU5OTk5OTl9.signature",
                "user": {
                    "id": 1,
                    "username": "admin",
                    "email": "admin@taller.com",
                    "roles": ["ADMIN"],
                },
            }
        }


class RefreshRequest(BaseModel):
    """Request para refrescar access token."""

    refresh_token: str = Field(..., min_length=1, description="Refresh token JWT")

    class Config:
        json_schema_extra = {
            "example": {
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIiwidHlwZSI6InJlZnJlc2giLCJleHAiOjE3MTU5OTk5OTl9.signature"
            }
        }


class RefreshResponse(BaseModel):
    """Response con nuevo access token."""

    access_token: str = Field(..., description="Nuevo JWT access token (15 min expiry)")

    class Config:
        json_schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIiwicm9sZXMiOlsiQURNSU4iXSwiZXhwIjoxNzE0OTk5OTk5fQ.new_signature"
            }
        }


class LogoutRequest(BaseModel):
    """Request para logout (invalidar refresh token)."""

    refresh_token: str = Field(..., min_length=1)


class ForgotPasswordRequest(BaseModel):
    """Request para solicitar recuperación de contraseña."""

    email: str = Field(..., min_length=3, max_length=100)

    @validator("email")
    def validate_email_format(cls, v):
        """Valida formato básico de email."""
        if "@" not in v or "." not in v.split("@")[-1]:
            raise ValueError("Formato de email inválido")
        return v.lower()


class ForgotPasswordResponse(BaseModel):
    """Response genérico para forgot password (no revela si email existe)."""

    message: str


class ResetPasswordRequest(BaseModel):
    """Request para resetear contraseña con token."""

    token: str = Field(..., min_length=1, description="Token de recuperación recibido por email")
    new_password: str = Field(..., min_length=8, max_length=100, description="Nueva contraseña")

    @validator("new_password")
    def validate_password_complexity(cls, v):
        """
        Valida complejidad de contraseña:
        - Mínimo 8 caracteres
        - Al menos una mayúscula
        - Al menos una minúscula
        - Al menos un número
        """
        if len(v) < 8:
            raise ValueError("La contraseña debe tener al menos 8 caracteres")

        if not any(c.isupper() for c in v):
            raise ValueError("La contraseña debe contener al menos una letra mayúscula")

        if not any(c.islower() for c in v):
            raise ValueError("La contraseña debe contener al menos una letra minúscula")

        if not any(c.isdigit() for c in v):
            raise ValueError("La contraseña debe contener al menos un número")

        return v

    class Config:
        json_schema_extra = {
            "example": {"token": "abc123def456ghi789", "new_password": "NewSecurePass123!"}
        }


class ResetPasswordResponse(BaseModel):
    """Response de reset password exitoso."""

    message: str
