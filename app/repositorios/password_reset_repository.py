"""
Repositorio de acceso a datos de tokens de recuperación de contraseña.

Este módulo implementa el patrón Repository para abstraer
el acceso a datos de la tabla password_reset_tokens.
"""

from datetime import datetime

from sqlalchemy.orm import Session

from app.modelos.password_reset_token import PasswordResetToken


class PasswordResetTokenRepository:
    """
    Repositorio de acceso a datos de tokens de recuperación de contraseña.

    Abstrae todas las operaciones de base de datos relacionadas
    con password_reset_tokens, facilitando testing y reutilización de queries.

    Este repositorio maneja tokens únicos con expiración de 1 hora para
    recuperación de contraseña. Los tokens deben ser invalidados después de usarse.
    """

    def __init__(self, db: Session):
        """
        Inicializa el repositorio con una sesión de base de datos.

        Args:
            db: Sesión de SQLAlchemy
        """
        self.db = db

    def create(self, token: PasswordResetToken) -> PasswordResetToken:
        """
        Crea un nuevo token de recuperación de contraseña.

        Args:
            token: Objeto PasswordResetToken a crear

        Returns:
            Token creado con ID asignado
        """
        self.db.add(token)
        self.db.commit()
        self.db.refresh(token)
        return token

    def get_by_token(self, token: str) -> PasswordResetToken | None:
        """
        Obtiene un token de recuperación por su valor.

        Args:
            token: Valor del token (hash SHA256)

        Returns:
            Token si existe, None en caso contrario
        """
        return self.db.query(PasswordResetToken).filter(PasswordResetToken.token == token).first()

    def get_by_user_id(self, user_id: int) -> list[PasswordResetToken]:
        """
        Obtiene todos los tokens de recuperación de un usuario.

        Útil para invalidar todos los tokens de un usuario cuando
        se cambia la contraseña exitosamente.

        Args:
            user_id: ID del usuario

        Returns:
            Lista de tokens del usuario
        """
        return self.db.query(PasswordResetToken).filter(PasswordResetToken.user_id == user_id).all()

    def mark_as_used(self, token: PasswordResetToken) -> PasswordResetToken:
        """
        Marca un token como usado.

        Los tokens usados no pueden ser reutilizados para prevenir
        ataques de replay.

        Args:
            token: Token a marcar como usado

        Returns:
            Token actualizado
        """
        token.used = True  # type: ignore[assignment]
        self.db.commit()
        self.db.refresh(token)
        return token

    def invalidate_user_tokens(self, user_id: int) -> int:
        """
        Invalida todos los tokens de recuperación de un usuario.

        Marca todos los tokens no usados del usuario como usados.
        Útil cuando se cambia la contraseña exitosamente o cuando
        se detecta actividad sospechosa.

        Args:
            user_id: ID del usuario

        Returns:
            Número de tokens invalidados
        """
        count = (
            self.db.query(PasswordResetToken)
            .filter(PasswordResetToken.user_id == user_id, PasswordResetToken.used == False)
            .update({"used": True}, synchronize_session=False)
        )
        self.db.commit()
        return count

    def cleanup_expired(self) -> int:
        """
        Elimina tokens expirados de la base de datos.

        Los tokens expirados ya no pueden ser usados, por lo que
        pueden ser eliminados de forma segura. Esta operación
        debe ejecutarse periódicamente (cron job cada 24h) para
        mantener la tabla limpia y optimizada.

        Returns:
            Número de tokens eliminados
        """
        now = datetime.now()

        # Contar tokens a eliminar
        count = (
            self.db.query(PasswordResetToken).filter(PasswordResetToken.expires_at < now).count()
        )

        # Eliminar tokens expirados
        self.db.query(PasswordResetToken).filter(PasswordResetToken.expires_at < now).delete(
            synchronize_session=False
        )

        self.db.commit()

        return count
