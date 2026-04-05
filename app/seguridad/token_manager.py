"""
Token Manager for JWT generation, validation and decoding.

This module provides JWT token management with access tokens (15 min)
and refresh tokens (7 days) using PyJWT library.
"""

import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from jwt.exceptions import InvalidTokenError, ExpiredSignatureError

from app.modelos.user import User


class TokenManager:
    """
    Maneja generación, validación y decodificación de tokens JWT.
    
    Genera access tokens (15 min) y refresh tokens (7 días) con
    firma HMAC-SHA256. Incluye validación de firma, expiración
    y estructura del payload.
    """
    
    def __init__(
        self,
        secret_key: Optional[str] = None,
        algorithm: str = "HS256",
        access_token_expire_minutes: int = 15,
        refresh_token_expire_days: int = 7
    ):
        """
        Inicializa el TokenManager con configuración de JWT.
        
        Args:
            secret_key: Clave secreta para firmar tokens (mínimo 32 caracteres).
                       Si no se provee, se lee de JWT_SECRET_KEY env var.
            algorithm: Algoritmo de firma (default: HS256)
            access_token_expire_minutes: Minutos de expiración para access tokens
            refresh_token_expire_days: Días de expiración para refresh tokens
        """
        self.secret_key = secret_key or os.getenv("JWT_SECRET_KEY")
        if not self.secret_key:
            raise ValueError("JWT_SECRET_KEY must be set in environment or provided")
        if len(self.secret_key) < 32:
            raise ValueError("JWT_SECRET_KEY must be at least 32 characters long")
        
        self.algorithm = algorithm
        self.access_token_expire_minutes = access_token_expire_minutes
        self.refresh_token_expire_days = refresh_token_expire_days
    
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
        
        Args:
            user: Usuario autenticado con roles cargados
            
        Returns:
            Token JWT firmado
            
        Example:
            >>> token_manager = TokenManager()
            >>> user = User(id=1, username="admin")
            >>> token = token_manager.generate_access_token(user)
            >>> print(token)
            eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
        """
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(minutes=self.access_token_expire_minutes)
        
        # Extraer nombres de roles del usuario
        role_names = [role.name for role in user.roles] if user.roles else []
        
        payload = {
            "user_id": user.id,
            "username": user.username,
            "roles": role_names,
            "exp": expires_at,
            "iat": now,
            "jti": str(uuid.uuid4()),
            "token_type": "access"
        }
        
        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
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
        
        Args:
            user: Usuario autenticado
            
        Returns:
            Refresh token JWT firmado
            
        Example:
            >>> token_manager = TokenManager()
            >>> user = User(id=1, username="admin")
            >>> refresh_token = token_manager.generate_refresh_token(user)
        """
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(days=self.refresh_token_expire_days)
        
        payload = {
            "user_id": user.id,
            "jti": str(uuid.uuid4()),
            "exp": expires_at,
            "iat": now,
            "token_type": "refresh"
        }
        
        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        return token
    
    def decode_token(self, token: str) -> dict:
        """
        Decodifica y valida un token JWT.
        
        Verifica:
        - Firma válida
        - No expirado
        - Estructura correcta
        
        Args:
            token: Token JWT
            
        Returns:
            Payload del token decodificado
            
        Raises:
            InvalidTokenError: Si el token es inválido o la firma no coincide
            ExpiredSignatureError: Si el token expiró
            
        Example:
            >>> token_manager = TokenManager()
            >>> payload = token_manager.decode_token(token)
            >>> print(payload["user_id"])
            1
        """
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm]
            )
            return payload
        except ExpiredSignatureError:
            raise ExpiredSignatureError("Token has expired")
        except InvalidTokenError as e:
            raise InvalidTokenError(f"Invalid token: {str(e)}")
    
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
            "refresh_token": self.generate_refresh_token(user)
        }
