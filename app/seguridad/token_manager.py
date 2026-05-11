"""
Token Manager for JWT generation, validation and decoding.

This module provides JWT token management with access tokens (15 min)
and refresh tokens (7 days) using PyJWT library.

Supports multi-key JWT verification for key rotation with grace period.
"""

import os
import uuid
from datetime import UTC, datetime, timedelta

import jwt
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError

from app.modelos.user import User

# Importar JWTKeyEntry solo para type hints, evitando import circular
try:
    from app.configuracion.secrets_manager import JWTKeyEntry
except ImportError:
    JWTKeyEntry = None  # type: ignore


class TokenManager:
    """
    Maneja generación, validación y decodificación de tokens JWT.

    Genera access tokens (15 min) y refresh tokens (7 días) con
    firma HMAC-SHA256. Incluye validación de firma, expiración
    y estructura del payload.

    Soporta verificación multi-clave para rotación de claves JWT con
    período de gracia. Si se pasan ``keys``, se usa la clave activa
    (``is_active=True``) para firmar y se intentan todas las claves
    para verificar. Si se pasa ``secret_key`` string, se crea
    internamente un ``JWTKeyEntry`` con ``is_active=True`` para
    mantener compatibilidad total con el uso anterior.
    """

    def __init__(
        self,
        secret_key: str | None = None,
        algorithm: str = "HS256",
        access_token_expire_minutes: int = 15,
        refresh_token_expire_days: int = 7,
        keys: list | None = None,
    ):
        """
        Inicializa el TokenManager con configuración de JWT.

        Args:
            secret_key: Clave secreta para firmar tokens (mínimo 32 caracteres).
                       Si no se provee, se intenta recuperar desde SecretsManager
                       o JWT_SECRET_KEY env var. Ignorado si se pasa ``keys``.
            algorithm: Algoritmo de firma (default: HS256)
            access_token_expire_minutes: Minutos de expiración para access tokens
            refresh_token_expire_days: Días de expiración para refresh tokens
            keys: Lista de JWTKeyEntry para soporte multi-clave. Si se provee,
                  tiene precedencia sobre ``secret_key``. Debe contener exactamente
                  una entrada con ``is_active=True`` para firmar nuevos tokens.

        Raises:
            ValueError: Si no hay clave disponible, la clave es demasiado corta,
                        o no hay ninguna clave activa en la lista ``keys``.
        """
        from app.configuracion.secrets_manager import JWTKeyEntry as _JWTKeyEntry

        self.algorithm = algorithm
        self.access_token_expire_minutes = access_token_expire_minutes
        self.refresh_token_expire_days = refresh_token_expire_days

        if keys is not None:
            # Modo multi-clave: usar la lista de JWTKeyEntry proporcionada
            if not keys:
                raise ValueError(
                    "La lista de claves JWT no puede estar vacía. "
                    "Proporcionar al menos una clave con is_active=True."
                )
            active_keys = [k for k in keys if k.is_active]
            if not active_keys:
                raise ValueError(
                    "No hay ninguna clave JWT activa (is_active=True) en la lista. "
                    "Exactamente una clave debe tener is_active=True para firmar tokens."
                )
            self.keys: list = list(keys)
            # Mantener secret_key apuntando a la clave activa para compatibilidad
            self.secret_key = active_keys[0].key
        else:
            # Modo compatibilidad: secret_key string → crear JWTKeyEntry interno
            resolved_key: str | None = None

            if secret_key:
                resolved_key = secret_key
            else:
                # Intentar recuperar desde SecretsManager
                try:
                    from app.configuracion.secrets_manager import SecretsManager

                    secrets_manager = SecretsManager()
                    resolved_key = secrets_manager.get_secret(
                        "jwt-secret-key", fallback_env_var="JWT_SECRET_KEY"
                    )
                except Exception:
                    # Fallback a variable de entorno directamente
                    resolved_key = os.getenv("JWT_SECRET_KEY")

            if not resolved_key:
                raise ValueError("JWT_SECRET_KEY must be set in environment or provided")
            if len(resolved_key) < 32:
                raise ValueError("JWT_SECRET_KEY must be at least 32 characters long")

            self.secret_key = resolved_key
            # Crear JWTKeyEntry interno para unificar la lógica de firma/verificación
            self.keys = [
                _JWTKeyEntry(
                    version="legacy",
                    key=resolved_key,
                    created_at=datetime.now(UTC),
                    is_active=True,
                )
            ]

    @property
    def _active_key(self):
        """Retorna la JWTKeyEntry con is_active=True para firmar nuevos tokens."""
        for key_entry in self.keys:
            if key_entry.is_active:
                return key_entry
        raise ValueError("No hay ninguna clave JWT activa (is_active=True).")

    def generate_access_token(self, user: User) -> str:
        """
        Genera un access token JWT con expiración de 15 minutos.

        Payload incluye:
        - user_id: ID del usuario
        - username: Nombre de usuario
        - roles: Lista de roles del usuario
        - exp: Timestamp de expiración (15 min)
        - iat: Timestamp de emisión
        - jti: JWT ID único (UUID)
        - kid: Key version ID (identifica qué clave firmó el token)

        Args:
            user: Usuario autenticado con roles cargados

        Returns:
            Token JWT firmado con la clave activa (is_active=True)

        Example:
            >>> token_manager = TokenManager()
            >>> user = User(id=1, username="admin")
            >>> token = token_manager.generate_access_token(user)
            >>> print(token)
            eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
        """
        now = datetime.now(UTC)
        expires_at = now + timedelta(minutes=self.access_token_expire_minutes)

        # Extraer nombres de roles del usuario
        role_names = [role.name for role in user.roles] if user.roles else []

        # Obtener la clave activa para firmar
        active_key = self._active_key

        payload = {
            "user_id": user.id,
            "username": user.username,
            "roles": role_names,
            "taller_id": user.taller_id,  # RLS: aislamiento multi-tenant
            "exp": expires_at,
            "iat": now,
            "jti": str(uuid.uuid4()),
            "token_type": "access",
            "kid": active_key.version,  # Key version ID
        }

        token = jwt.encode(payload, active_key.key, algorithm=self.algorithm)
        return token

    def generate_refresh_token(self, user: User) -> str:
        """
        Genera un refresh token JWT con expiración de 7 días.

        Payload incluye:
        - user_id: ID del usuario
        - jti: JWT ID único (UUID)
        - exp: Timestamp de expiración (7 días)
        - iat: Timestamp de emisión
        - token_type: "refresh"
        - kid: Key version ID (identifica qué clave firmó el token)

        Args:
            user: Usuario autenticado

        Returns:
            Refresh token JWT firmado con la clave activa (is_active=True)

        Example:
            >>> token_manager = TokenManager()
            >>> user = User(id=1, username="admin")
            >>> refresh_token = token_manager.generate_refresh_token(user)
        """
        now = datetime.now(UTC)
        expires_at = now + timedelta(days=self.refresh_token_expire_days)

        # Obtener la clave activa para firmar
        active_key = self._active_key

        payload = {
            "user_id": user.id,
            "jti": str(uuid.uuid4()),
            "exp": expires_at,
            "iat": now,
            "token_type": "refresh",
            "kid": active_key.version,  # Key version ID
        }

        token = jwt.encode(payload, active_key.key, algorithm=self.algorithm)
        return token

    def decode_token(self, token: str) -> dict:
        """
        Decodifica y valida un token JWT.

        Intenta verificar el token con cada clave disponible, ordenadas por
        ``created_at`` descendente (más reciente primero). Si el token está
        expirado, relanza ``ExpiredSignatureError`` inmediatamente sin intentar
        otras claves (la expiración es definitiva). Si todas las claves fallan,
        relanza el último ``InvalidTokenError``.

        Verifica:
        - Firma válida (con alguna de las claves disponibles)
        - No expirado
        - Estructura correcta

        Args:
            token: Token JWT

        Returns:
            Payload del token decodificado

        Raises:
            ExpiredSignatureError: Si el token expiró (definitivo, no se reintenta)
            InvalidTokenError: Si el token es inválido con todas las claves disponibles

        Example:
            >>> token_manager = TokenManager()
            >>> payload = token_manager.decode_token(token)
            >>> print(payload["user_id"])
            1
        """
        last_error = None
        for key_entry in sorted(self.keys, key=lambda k: k.created_at, reverse=True):
            try:
                return jwt.decode(token, key_entry.key, algorithms=[self.algorithm])
            except ExpiredSignatureError:
                # Expirado es definitivo — no tiene sentido intentar otras claves
                raise
            except InvalidTokenError as e:
                last_error = e
                continue

        raise InvalidTokenError(
            f"Token inválido con todas las claves activas: {last_error}"
        )

    def generate_tokens(self, user: User) -> dict:
        """
        Genera ambos tokens (access y refresh) para un usuario.

        Método de conveniencia que genera access_token y refresh_token
        en una sola llamada.

        Args:
            user: Usuario autenticado

        Returns:
            Dict con access_token y refresh_token

        Example:
            >>> token_manager = TokenManager()
            >>> tokens = token_manager.generate_tokens(user)
            >>> print(tokens["access_token"])
            >>> print(tokens["refresh_token"])
        """
        return {
            "access_token": self.generate_access_token(user),
            "refresh_token": self.generate_refresh_token(user),
        }
