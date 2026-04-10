"""
Endpoints de autenticación JWT.

Implementa los endpoints para login, refresh, logout, forgot password
y reset password usando AuthService.
"""

import os
from fastapi import APIRouter, Request, Depends, HTTPException, status, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.configuracion.base_datos import obtener_db
from app.configuracion.limiter import limiter
from app.esquemas.auth_schema import (
    LoginRequest,
    LoginResponse,
    RefreshRequest,
    RefreshResponse,
    LogoutRequest,
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    ResetPasswordRequest,
    ResetPasswordResponse
)
from app.servicios.auth_service import (
    AuthService,
    InvalidCredentialsError,
    InvalidTokenError
)
from app.servicios.audit_service import AuditService
from app.repositorios.user_repository import UserRepository
from app.repositorios.token_blacklist_repository import TokenBlacklistRepository
from app.repositorios.password_reset_repository import PasswordResetTokenRepository
from app.repositorios.audit_log_repository import AuditLogRepository
from app.seguridad.token_manager import TokenManager
from app.seguridad.password_hasher import PasswordHasher
from app.seguridad.auth_middleware import require_auth
from app.servicios.email_service import enviar_recuperacion_contrasena


router = APIRouter(prefix="/auth", tags=["Authentication"])


def get_auth_service(db: Session = Depends(obtener_db)) -> AuthService:
    """
    Dependency para obtener instancia de AuthService.
    
    Args:
        db: Sesión de base de datos
        
    Returns:
        AuthService configurado con todas sus dependencias
    """
    user_repo = UserRepository(db)
    token_manager = TokenManager()
    password_hasher = PasswordHasher()
    audit_log_repo = AuditLogRepository(db)
    audit_service = AuditService(audit_log_repo)
    token_blacklist_repo = TokenBlacklistRepository(db)
    password_reset_repo = PasswordResetTokenRepository(db)
    
    return AuthService(
        user_repo=user_repo,
        token_manager=token_manager,
        password_hasher=password_hasher,
        audit_service=audit_service,
        token_blacklist_repo=token_blacklist_repo,
        password_reset_repo=password_reset_repo
    )


def get_client_info(request: Request) -> dict:
    """
    Extrae información del cliente del request.
    
    Args:
        request: Request de FastAPI
        
    Returns:
        Dict con ip_address y user_agent
    """
    ip_address = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")
    
    return {
        "ip_address": ip_address,
        "user_agent": user_agent
    }


@router.post("/login", response_model=LoginResponse, status_code=status.HTTP_200_OK)
@limiter.limit(f"{os.getenv('RATE_LIMIT_AUTH_PER_MINUTE', '5')}/minute")
async def login(
    request: Request,
    response: Response,
    login_data: LoginRequest,
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Autentica un usuario y retorna tokens JWT.
    
    Rate limit: 5 requests/minuto por IP (configurable con RATE_LIMIT_AUTH_PER_MINUTE).
    
    Proceso:
    1. Valida credenciales (username/password)
    2. Genera access_token y refresh_token
    3. Registra evento LOGIN en audit_log con IP y user agent
    4. Retorna tokens y datos del usuario
    5. Configura refresh_token como cookie segura en producción
    
    Args:
        request: Request de FastAPI (para obtener IP y user agent)
        response: Response de FastAPI (para configurar cookies)
        login_data: Credenciales del usuario
        auth_service: Servicio de autenticación
        
    Returns:
        LoginResponse con access_token, refresh_token y user
        
    Raises:
        HTTPException 401: Si las credenciales son inválidas
        HTTPException 429: Si se excede el rate limit
    """
    client_info = get_client_info(request)
    
    try:
        result = auth_service.authenticate(
            username=login_data.username,
            password=login_data.password,
            ip_address=client_info["ip_address"],
            user_agent=client_info["user_agent"]
        )
        
        # Configurar refresh_token como cookie segura
        is_production = os.getenv("ENVIRONMENT") == "production"
        response.set_cookie(
            key="refresh_token",
            value=result["refresh_token"],
            httponly=True,
            secure=is_production,  # Solo HTTPS en producción
            samesite="strict",     # Protección CSRF
            max_age=7*24*60*60     # 7 días
        )
        
        return LoginResponse(**result)
    
    except InvalidCredentialsError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )


@router.post("/refresh", response_model=RefreshResponse, status_code=status.HTTP_200_OK)
@limiter.limit(f"{os.getenv('RATE_LIMIT_REFRESH_PER_MINUTE', '10')}/minute")
async def refresh(
    request: Request,
    refresh_data: RefreshRequest,
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Genera un nuevo access token usando un refresh token válido.
    
    Rate limit: 10 requests/minuto por IP (configurable con RATE_LIMIT_REFRESH_PER_MINUTE).
    
    Proceso:
    1. Valida refresh_token
    2. Verifica que no esté en lista negra
    3. Genera nuevo access_token
    
    Args:
        request: Request de FastAPI (para rate limiting)
        refresh_data: Refresh token
        auth_service: Servicio de autenticación
        
    Returns:
        RefreshResponse con nuevo access_token
        
    Raises:
        HTTPException 401: Si el refresh token es inválido o expiró
        HTTPException 429: Si se excede el rate limit
    """
    try:
        new_access_token = auth_service.refresh_access_token(
            refresh_token=refresh_data.refresh_token
        )
        
        return RefreshResponse(access_token=new_access_token)
    
    except InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
@require_auth
async def logout(
    request: Request,
    logout_data: LogoutRequest,
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Invalida un refresh token (logout).
    
    Requiere autenticación con @require_auth.
    
    Proceso:
    1. Obtiene user_id de request.state.user
    2. Agrega refresh_token a lista negra
    3. Registra evento LOGOUT en audit_log
    
    Args:
        request: Request de FastAPI (contiene user autenticado)
        logout_data: Refresh token a invalidar
        auth_service: Servicio de autenticación
        
    Returns:
        204 No Content
        
    Raises:
        HTTPException 401: Si no está autenticado o token inválido
    """
    user = request.state.user
    client_info = get_client_info(request)
    
    try:
        auth_service.logout(
            refresh_token=logout_data.refresh_token,
            user_id=user.id,
            ip_address=client_info["ip_address"],
            user_agent=client_info["user_agent"]
        )
    
    except InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )


@router.post("/forgot-password", response_model=ForgotPasswordResponse, status_code=status.HTTP_200_OK)
@limiter.limit(f"{os.getenv('RATE_LIMIT_FORGOT_PASSWORD_PER_HOUR', '3')}/hour")
async def forgot_password(
    request: Request,
    forgot_data: ForgotPasswordRequest,
    db: Session = Depends(obtener_db),
    auth_service: AuthService = Depends(get_auth_service)
):
    token = auth_service.forgot_password(email=forgot_data.email)
    if token:
        from app.repositorios.user_repository import UserRepository
        user = UserRepository(db).get_by_email(forgot_data.email)
        nombre = (user.nombre_completo or user.username) if user else ""
        enviar_recuperacion_contrasena(destinatario=forgot_data.email, token=token, nombre=nombre)
    return ForgotPasswordResponse(
        message="Si el email existe en nuestro sistema, recibirás instrucciones para recuperar tu contraseña"
    )


class ForgotPasswordByUsernameRequest(BaseModel):
    username: str


@router.post("/forgot-password-by-username", response_model=ForgotPasswordResponse, status_code=status.HTTP_200_OK)
@limiter.limit(f"{os.getenv('RATE_LIMIT_FORGOT_PASSWORD_PER_HOUR', '3')}/hour")
async def forgot_password_by_username(
    request: Request,
    data: ForgotPasswordByUsernameRequest,
    db: Session = Depends(obtener_db),
    auth_service: AuthService = Depends(get_auth_service)
):
    """Recuperación por username: envía el email al correo registrado del usuario."""
    from app.repositorios.user_repository import UserRepository
    user = UserRepository(db).get_by_username(data.username)
    if user and user.email:
        token = auth_service.forgot_password(email=user.email)
        if token:
            nombre = user.nombre_completo or user.username
            enviar_recuperacion_contrasena(destinatario=user.email, token=token, nombre=nombre)
    # Siempre mismo mensaje
    return ForgotPasswordResponse(
        message="Si el usuario existe, se enviará un enlace al correo registrado"
    )


@router.post("/reset-password", response_model=ResetPasswordResponse, status_code=status.HTTP_200_OK)
async def reset_password(
    request: Request,
    reset_data: ResetPasswordRequest,
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Resetea contraseña usando token de recuperación.
    
    Proceso:
    1. Valida token de recuperación
    2. Valida complejidad de nueva contraseña (validador Pydantic)
    3. Actualiza contraseña del usuario
    4. Invalida todos los tokens activos
    5. Registra evento PASSWORD_RESET en audit_log
    
    Args:
        request: Request de FastAPI (para obtener IP y user agent)
        reset_data: Token y nueva contraseña
        auth_service: Servicio de autenticación
        
    Returns:
        ResetPasswordResponse con mensaje de éxito
        
    Raises:
        HTTPException 400: Si el token es inválido o la contraseña no cumple requisitos
    """
    client_info = get_client_info(request)
    
    try:
        auth_service.reset_password(
            token=reset_data.token,
            new_password=reset_data.new_password,
            ip_address=client_info["ip_address"],
            user_agent=client_info["user_agent"]
        )
        
        return ResetPasswordResponse(
            message="Contraseña actualizada exitosamente"
        )
    
    except InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
