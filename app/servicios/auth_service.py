"""
Servicio de autenticación y gestión de sesiones.

Este módulo implementa la lógica de negocio para autenticación JWT,
gestión de tokens, recuperación de contraseña y migración automática
de contraseñas SHA256 a bcrypt.
"""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.modelos.user import User
from app.modelos.password_reset_token import PasswordResetToken
from app.repositorios.user_repository import UserRepository
from app.repositorios.token_blacklist_repository import TokenBlacklistRepository
from app.repositorios.password_reset_repository import PasswordResetTokenRepository
from app.servicios.audit_service import AuditService
from app.servicios.security_detection_service import SecurityDetectionService
from app.seguridad.password_hasher import PasswordHasher
from app.seguridad.token_manager import TokenManager


class InvalidCredentialsError(Exception):
    """Excepción lanzada cuando las credenciales son inválidas."""
    pass


class InvalidTokenError(Exception):
    """Excepción lanzada cuando un token es inválido o expiró."""
    pass


class AuthService:
    """
    Servicio de autenticación y gestión de sesiones.
    
    Maneja login, logout, refresh de tokens, recuperación de contraseña
    y migración automática de contraseñas SHA256 a bcrypt.
    
    Todos los eventos de autenticación se registran en audit_log para
    trazabilidad y seguridad.
    """
    
    def __init__(
        self,
        user_repo: UserRepository,
        token_manager: TokenManager,
        password_hasher: PasswordHasher,
        audit_service: AuditService,
        token_blacklist_repo: TokenBlacklistRepository,
        password_reset_repo: PasswordResetTokenRepository,
        security_detection_service: Optional[SecurityDetectionService] = None
    ):
        """
        Inicializa el servicio de autenticación.
        
        Args:
            user_repo: Repositorio de usuarios
            token_manager: Gestor de tokens JWT
            password_hasher: Hasher de contraseñas
            audit_service: Servicio de auditoría
            token_blacklist_repo: Repositorio de tokens en lista negra
            password_reset_repo: Repositorio de tokens de recuperación
            security_detection_service: Servicio de detección de seguridad (opcional)
        """
        self.user_repo = user_repo
        self.token_manager = token_manager
        self.password_hasher = password_hasher
        self.audit_service = audit_service
        self.token_blacklist_repo = token_blacklist_repo
        self.password_reset_repo = password_reset_repo
        self.security_detection_service = security_detection_service
    
    def _verify_sha256_password(self, password: str, password_hash: str) -> bool:
        """
        Verifica una contraseña contra un hash SHA256 (sistema legacy).
        
        Args:
            password: Contraseña en texto plano
            password_hash: Hash SHA256 almacenado
            
        Returns:
            True si la contraseña es correcta
        """
        computed_hash = hashlib.sha256(password.encode('utf-8')).hexdigest()
        return computed_hash == password_hash
    
    def _is_sha256_hash(self, password_hash: str) -> bool:
        """
        Detecta si un hash es SHA256 (64 caracteres hexadecimales).
        
        Args:
            password_hash: Hash a verificar
            
        Returns:
            True si es SHA256, False si es bcrypt
        """
        return len(password_hash) == 64 and all(c in '0123456789abcdef' for c in password_hash)
    
    def authenticate(
        self,
        username: str,
        password: str,
        ip_address: str,
        user_agent: str
    ) -> dict:
        """
        Autentica un usuario y genera tokens JWT.
        
        Proceso:
        1. Busca usuario por username
        2. Verifica contraseña (SHA256 o bcrypt según is_migrated)
        3. Si es SHA256, migra automáticamente a bcrypt
        4. Genera access_token y refresh_token
        5. Registra evento LOGIN en audit_log
        
        Args:
            username: Nombre de usuario
            password: Contraseña en texto plano
            ip_address: IP del cliente
            user_agent: User agent del cliente
            
        Returns:
            Dict con access_token, refresh_token y user
            
        Raises:
            InvalidCredentialsError: Si las credenciales son incorrectas
                                    (mensaje genérico para prevenir enumeración)
        """
        # Buscar usuario
        user = self.user_repo.get_by_username(username)
        
        # Mensaje genérico para prevenir enumeración de usuarios
        generic_error = "Credenciales inválidas"
        
        if not user:
            # Registrar intento fallido sin revelar que el usuario no existe
            self.audit_service.log_event(
                user_id=None,
                action="LOGIN_FAILED",
                resource_type="auth",
                resource_id=None,
                ip_address=ip_address,
                user_agent=user_agent,
                details={"username": username, "reason": "user_not_found"}
            )
            raise InvalidCredentialsError(generic_error)
        
        # Verificar si usuario está activo
        if not user.is_active:
            self.audit_service.log_event(
                user_id=user.id,
                action="LOGIN_FAILED",
                resource_type="auth",
                resource_id=user.id,
                ip_address=ip_address,
                user_agent=user_agent,
                details={"username": username, "reason": "user_inactive"}
            )
            raise InvalidCredentialsError(generic_error)
        
        # Verificar contraseña según el tipo de hash
        password_valid = False
        needs_migration = False
        
        if self._is_sha256_hash(user.password_hash):
            # Contraseña legacy SHA256
            password_valid = self._verify_sha256_password(password, user.password_hash)
            needs_migration = password_valid  # Migrar si la contraseña es correcta
        else:
            # Contraseña bcrypt
            password_valid = self.password_hasher.verify_password(password, user.password_hash)
        
        if not password_valid:
            # Registrar intento fallido
            self.audit_service.log_event(
                user_id=user.id,
                action="LOGIN_FAILED",
                resource_type="auth",
                resource_id=user.id,
                ip_address=ip_address,
                user_agent=user_agent,
                details={"username": username, "reason": "invalid_password"}
            )
            
            # Detectar intentos de fuerza bruta
            if self.security_detection_service:
                self.security_detection_service.detect_brute_force(ip_address)
            
            raise InvalidCredentialsError(generic_error)
        
        # Migración automática de SHA256 a bcrypt
        if needs_migration:
            new_hash = self.password_hasher.hash_password(password)
            user.password_hash = new_hash
            user.is_migrated = True
            self.user_repo.update(user)
            
            # Registrar migración exitosa
            self.audit_service.log_event(
                user_id=user.id,
                action="PASSWORD_MIGRATED",
                resource_type="user",
                resource_id=user.id,
                ip_address=ip_address,
                user_agent=user_agent,
                details={"from": "SHA256", "to": "bcrypt"}
            )
        
        # Generar tokens JWT
        tokens = self.token_manager.generate_tokens(user)
        
        # Registrar login exitoso
        self.audit_service.log_event(
            user_id=user.id,
            action="LOGIN",
            resource_type="auth",
            resource_id=user.id,
            ip_address=ip_address,
            user_agent=user_agent,
            details={"username": username}
        )
        
        return {
            "access_token": tokens["access_token"],
            "refresh_token": tokens["refresh_token"],
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "roles": [role.name for role in user.roles] if user.roles else []
            }
        }
    
    def refresh_access_token(self, refresh_token: str) -> str:
        """
        Genera un nuevo access token usando un refresh token válido.
        
        Proceso:
        1. Decodifica y valida refresh_token
        2. Verifica que no esté en lista negra
        3. Verifica que el usuario existe y está activo
        4. Genera nuevo access_token
        
        Args:
            refresh_token: Refresh token JWT
            
        Returns:
            Nuevo access_token
            
        Raises:
            InvalidTokenError: Si el token es inválido, expiró o está en lista negra
        """
        try:
            # Decodificar y validar token
            payload = self.token_manager.decode_token(refresh_token)
        except Exception as e:
            raise InvalidTokenError(f"Token inválido: {str(e)}")
        
        # Verificar que es un refresh token
        if payload.get("token_type") != "refresh":
            raise InvalidTokenError("Token no es un refresh token")
        
        # Verificar que no está en lista negra
        jti = payload.get("jti")
        if not jti:
            raise InvalidTokenError("Token no tiene JTI")
        
        if self.token_blacklist_repo.is_blacklisted(jti):
            # Detectar intento de reuso de token
            user_id = payload.get("user_id")
            if self.security_detection_service and user_id:
                self.security_detection_service.detect_token_reuse(
                    jti=jti,
                    user_id=user_id,
                    ip_address=None,
                    user_agent=None
                )
            raise InvalidTokenError("Token ha sido revocado")
        
        # Obtener usuario
        user_id = payload.get("user_id")
        if not user_id:
            raise InvalidTokenError("Token no tiene user_id")
        
        user = self.user_repo.get_by_id(user_id)
        if not user:
            raise InvalidTokenError("Usuario no existe")
        
        if not user.is_active:
            raise InvalidTokenError("Usuario inactivo")
        
        # Generar nuevo access token
        new_access_token = self.token_manager.generate_access_token(user)
        
        return new_access_token
    
    def logout(
        self,
        refresh_token: str,
        user_id: int,
        ip_address: str,
        user_agent: str
    ):
        """
        Invalida un refresh token agregándolo a lista negra.
        
        Proceso:
        1. Decodifica refresh_token para obtener jti y exp
        2. Agrega jti a token_blacklist con expiración
        3. Registra evento LOGOUT en audit_log
        
        Args:
            refresh_token: Token a invalidar
            user_id: ID del usuario
            ip_address: IP del cliente
            user_agent: User agent del cliente
            
        Raises:
            InvalidTokenError: Si el token es inválido
        """
        try:
            # Decodificar token para obtener jti y exp
            payload = self.token_manager.decode_token(refresh_token)
        except Exception as e:
            raise InvalidTokenError(f"Token inválido: {str(e)}")
        
        jti = payload.get("jti")
        exp_timestamp = payload.get("exp")
        
        if not jti or not exp_timestamp:
            raise InvalidTokenError("Token no tiene JTI o expiración")
        
        # Convertir timestamp a datetime
        expires_at = datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)
        
        # Agregar a lista negra
        self.token_blacklist_repo.add_to_blacklist(
            jti=jti,
            token_type="refresh",
            user_id=user_id,
            expires_at=expires_at,
            reason="logout"
        )
        
        # Registrar logout
        self.audit_service.log_event(
            user_id=user_id,
            action="LOGOUT",
            resource_type="auth",
            resource_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            details={"jti": jti}
        )
    
    def forgot_password(self, email: str) -> Optional[str]:
        """
        Genera token de recuperación de contraseña.
        
        Proceso:
        1. Busca usuario por email (sin revelar si existe)
        2. Genera token único con expiración de 1 hora
        3. Almacena token en password_reset_tokens
        4. Retorna token para enviar por email
        
        IMPORTANTE: No revela si el email existe en el sistema para
        prevenir enumeración de usuarios.
        
        Args:
            email: Email del usuario
            
        Returns:
            Token de recuperación si el usuario existe, None en caso contrario
        """
        # Detectar abuso de solicitudes de reset
        if self.security_detection_service:
            self.security_detection_service.detect_password_reset_abuse(email)
        
        # Buscar usuario por email
        user = self.user_repo.get_by_email(email)
        
        # No revelar si el email existe
        if not user:
            return None
        
        # Generar token único (32 bytes = 64 caracteres hex)
        raw_token = secrets.token_hex(32)
        
        # Hashear token para almacenamiento (SHA256)
        token_hash = hashlib.sha256(raw_token.encode('utf-8')).hexdigest()
        
        # Calcular expiración (1 hora)
        expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
        
        # Crear registro de token
        reset_token = PasswordResetToken(
            user_id=user.id,
            token=token_hash,
            expires_at=expires_at,
            used=False
        )
        
        self.password_reset_repo.create(reset_token)
        
        # Retornar token sin hashear (se enviará por email)
        return raw_token
    
    def reset_password(
        self,
        token: str,
        new_password: str,
        ip_address: str,
        user_agent: str
    ):
        """
        Resetea contraseña usando token de recuperación.
        
        Proceso:
        1. Hashea token recibido y busca en BD
        2. Valida que no expiró y no fue usado
        3. Hashea nueva contraseña con bcrypt
        4. Actualiza contraseña del usuario
        5. Marca token como usado
        6. Invalida todos los tokens activos del usuario
        7. Registra evento PASSWORD_RESET en audit_log
        
        Args:
            token: Token de recuperación (sin hashear)
            new_password: Nueva contraseña en texto plano
            ip_address: IP del cliente
            user_agent: User agent del cliente
            
        Raises:
            InvalidTokenError: Si el token es inválido, expiró o ya fue usado
        """
        # Hashear token para buscar en BD
        token_hash = hashlib.sha256(token.encode('utf-8')).hexdigest()
        
        # Buscar token
        reset_token = self.password_reset_repo.get_by_token(token_hash)
        
        if not reset_token:
            raise InvalidTokenError("Token de recuperación inválido")
        
        # Verificar que no expiró
        now = datetime.now(timezone.utc)
        # Convertir expires_at a timezone-aware si es naive
        expires_at = reset_token.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        
        if expires_at < now:
            raise InvalidTokenError("Token de recuperación expirado")
        
        # Verificar que no fue usado
        if reset_token.used:
            raise InvalidTokenError("Token de recuperación ya fue usado")
        
        # Obtener usuario
        user = self.user_repo.get_by_id(reset_token.user_id)
        if not user:
            raise InvalidTokenError("Usuario no existe")
        
        # Hashear nueva contraseña
        new_hash = self.password_hasher.hash_password(new_password)
        
        # Actualizar contraseña
        user.password_hash = new_hash
        user.is_migrated = True
        self.user_repo.update(user)
        
        # Marcar token como usado
        self.password_reset_repo.mark_as_used(reset_token)
        
        # Invalidar todos los tokens activos del usuario
        # (esto requeriría agregar todos los tokens del usuario a la blacklist,
        # pero como no tenemos un registro de todos los tokens emitidos,
        # simplemente invalidamos los tokens de recuperación)
        self.password_reset_repo.invalidate_user_tokens(user.id)
        
        # Registrar evento
        self.audit_service.log_event(
            user_id=user.id,
            action="PASSWORD_RESET",
            resource_type="user",
            resource_id=user.id,
            ip_address=ip_address,
            user_agent=user_agent,
            details={"method": "password_reset_token"}
        )
