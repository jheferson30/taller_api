"""
Repositorio de acceso a datos de tokens en lista negra.

Este módulo implementa el patrón Repository para abstraer
el acceso a datos de la tabla token_blacklist.
"""

from typing import Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.modelos.token_blacklist import TokenBlacklist


class TokenBlacklistRepository:
    """
    Repositorio de acceso a datos de tokens invalidados.
    
    Abstrae todas las operaciones de base de datos relacionadas
    con token_blacklist, facilitando testing y reutilización de queries.
    
    Este repositorio maneja la lista negra de tokens JWT que han sido
    invalidados por logout, desactivación de usuario, o revocación manual.
    """
    
    def __init__(self, db: Session):
        """
        Inicializa el repositorio con una sesión de base de datos.
        
        Args:
            db: Sesión de SQLAlchemy
        """
        self.db = db
    
    def add_to_blacklist(
        self,
        jti: str,
        token_type: str,
        user_id: int,
        expires_at: datetime,
        reason: Optional[str] = None
    ) -> TokenBlacklist:
        """
        Agrega un token a la lista negra.
        
        Los tokens en lista negra no deben ser aceptados por el sistema
        incluso si su firma es válida y no han expirado.
        
        Args:
            jti: JWT ID único del token (UUID)
            token_type: Tipo de token (refresh, access)
            user_id: ID del usuario propietario del token
            expires_at: Timestamp de expiración del token
            reason: Razón de invalidación (logout, user_deactivated, etc.)
            
        Returns:
            Registro de TokenBlacklist creado
        """
        token_blacklist = TokenBlacklist(
            jti=jti,
            token_type=token_type,
            user_id=user_id,
            expires_at=expires_at,
            reason=reason
        )
        self.db.add(token_blacklist)
        self.db.commit()
        self.db.refresh(token_blacklist)
        return token_blacklist
    
    def is_blacklisted(self, jti: str) -> bool:
        """
        Verifica si un token está en lista negra.
        
        Esta operación debe ser muy rápida ya que se ejecuta
        en cada request autenticado. El índice en la columna jti
        optimiza esta consulta.
        
        Args:
            jti: JWT ID del token a verificar
            
        Returns:
            True si el token está en lista negra, False en caso contrario
        """
        result = (
            self.db.query(TokenBlacklist)
            .filter(TokenBlacklist.jti == jti)
            .first()
        )
        return result is not None
    
    def cleanup_expired(self) -> int:
        """
        Elimina tokens expirados de la lista negra.
        
        Los tokens expirados ya no pueden ser usados, por lo que
        no es necesario mantenerlos en la lista negra. Esta operación
        debe ejecutarse periódicamente (cron job cada 24h) para
        mantener la tabla limpia y optimizada.
        
        Returns:
            Número de tokens eliminados
        """
        # Usar datetime sin timezone para compatibilidad con SQLite
        now = datetime.now()
        
        # Contar tokens a eliminar
        count = (
            self.db.query(TokenBlacklist)
            .filter(TokenBlacklist.expires_at < now)
            .count()
        )
        
        # Eliminar tokens expirados
        self.db.query(TokenBlacklist).filter(
            TokenBlacklist.expires_at < now
        ).delete(synchronize_session=False)
        
        self.db.commit()
        
        return count
