import logging
import os
import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from azure.core.exceptions import ResourceNotFoundError
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

logger = logging.getLogger(__name__)

# Período de gracia: la clave anterior sigue siendo válida para verificación
# durante 7 días tras una rotación.
_GRACE_PERIOD_DAYS = 7

# La clave activa debe rotarse cuando supera 90 días de antigüedad.
_ROTATION_THRESHOLD_DAYS = 90

# TTL del lock Redis para evitar rotaciones concurrentes (segundos).
_ROTATION_LOCK_TTL = 300

# Nombre del lock Redis para rotación JWT.
_ROTATION_LOCK_KEY = "jwt_key_rotation_lock"


@dataclass
class JWTKeyEntry:
    """
    Representa una clave JWT con su metadatos de ciclo de vida.

    Attributes:
        version:    UUID v4 que identifica unívocamente esta clave.
        key:        La clave secreta (mínimo 64 caracteres).
        created_at: Momento de creación en UTC.
        is_active:  True si es la clave actual para firmar nuevos tokens.
                    False si es la clave anterior en período de gracia.
    """

    version: str
    key: str
    created_at: datetime
    is_active: bool


class SecretsManager:
    """
    Manages secrets retrieval from Azure Key Vault with fallback to environment variables.

    Usage:
        secrets = SecretsManager()
        db_password = secrets.get_secret("database-password")
    """

    def __init__(self) -> None:
        self.vault_url: str | None = os.getenv("AZURE_KEY_VAULT_URL")
        self.use_key_vault: bool = bool(self.vault_url)
        self.client: SecretClient | None = None

        if self.use_key_vault and self.vault_url is not None:
            credential = DefaultAzureCredential()
            self.client = SecretClient(vault_url=self.vault_url, credential=credential)

    def get_secret(self, secret_name: str, fallback_env_var: str | None = None) -> str:
        """
        Retrieve secret from Key Vault or fallback to environment variable.

        Args:
            secret_name: Name of secret in Key Vault (e.g., "admin-password")
            fallback_env_var: Environment variable name to use if Key Vault unavailable

        Returns:
            Secret value as string

        Raises:
            RuntimeError: If secret not found in either location
        """
        if self.use_key_vault and self.client is not None:
            try:
                secret = self.client.get_secret(secret_name)
                return secret.value or ""
            except ResourceNotFoundError:
                if fallback_env_var:
                    value = os.getenv(fallback_env_var)
                    if value:
                        return value
                raise RuntimeError(f"Secret '{secret_name}' not found in Key Vault")

        # Fallback to environment variable
        if fallback_env_var:
            value = os.getenv(fallback_env_var)
            if value:
                return value

        raise RuntimeError(f"Secret '{secret_name}' not configured")

    # ------------------------------------------------------------------
    # Soporte multi-clave JWT
    # ------------------------------------------------------------------

    def get_jwt_keys(self) -> list[JWTKeyEntry]:
        """
        Carga y retorna las claves JWT activas desde Key Vault o variables de entorno.

        Fuentes de claves (en orden de prioridad):
        1. Azure Key Vault: secretos ``jwt-secret-key`` y ``jwt-secret-key-previous``
        2. Variables de entorno: ``JWT_SECRET_KEY`` y ``JWT_SECRET_KEY_PREVIOUS``

        La clave anterior solo se incluye si está dentro del período de gracia de 7 días.
        Si no hay información de fecha disponible para la clave anterior, se incluye
        siempre (comportamiento conservador que evita invalidar sesiones activas).

        Returns:
            Lista de :class:`JWTKeyEntry` con al menos la clave activa.
            La clave activa tiene ``is_active=True``; la anterior, ``is_active=False``.

        Raises:
            RuntimeError: Si no hay ninguna clave activa disponible en ninguna fuente.
        """
        active_key_value = self._load_raw_secret(
            vault_name="jwt-secret-key",
            env_var="JWT_SECRET_KEY",
        )

        if not active_key_value:
            raise RuntimeError(
                "No hay ninguna JWT_SECRET_KEY disponible. "
                "Configurar en Azure Key Vault como 'jwt-secret-key' "
                "o como variable de entorno 'JWT_SECRET_KEY'."
            )

        active_entry = JWTKeyEntry(
            version=str(uuid.uuid4()),
            key=active_key_value,
            created_at=datetime.now(UTC),
            is_active=True,
        )

        keys: list[JWTKeyEntry] = [active_entry]

        # Intentar cargar la clave anterior
        previous_key_value = self._load_raw_secret(
            vault_name="jwt-secret-key-previous",
            env_var="JWT_SECRET_KEY_PREVIOUS",
        )

        if previous_key_value:
            previous_created_at = self._load_previous_key_timestamp()
            within_grace = self._is_within_grace_period(previous_created_at)

            if within_grace:
                previous_entry = JWTKeyEntry(
                    version=str(uuid.uuid4()),
                    key=previous_key_value,
                    # Si no hay timestamp, usamos el límite del grace period como
                    # fecha conservadora para que no se descarte prematuramente.
                    created_at=previous_created_at or datetime.now(UTC),
                    is_active=False,
                )
                keys.append(previous_entry)

        return keys

    def check_rotation_needed(self) -> bool:
        """
        Evalúa si la clave JWT activa necesita ser rotada.

        Retorna ``True`` si la clave activa tiene más de 90 días de antigüedad.
        Si no hay información de fecha disponible, retorna ``False`` (comportamiento
        conservador: no forzar rotación cuando no se puede determinar la antigüedad).

        Returns:
            ``True`` si se debe rotar la clave; ``False`` en caso contrario.
        """
        created_at = self._load_active_key_timestamp()
        if created_at is None:
            # Sin información de fecha no podemos determinar si es necesario rotar.
            return False

        age = datetime.now(UTC) - created_at
        return age > timedelta(days=_ROTATION_THRESHOLD_DAYS)

    def rotate_jwt_key(self) -> str:
        """
        Genera una nueva clave JWT, archiva la actual como ``previous`` y registra
        el evento en el audit log.

        El proceso está protegido por un lock Redis (``jwt_key_rotation_lock``) con
        TTL de 300 segundos para evitar rotaciones concurrentes en entornos con
        múltiples instancias.

        Returns:
            La nueva clave JWT generada (64 caracteres hexadecimales).

        Raises:
            RuntimeError: Si no se puede adquirir el lock de rotación (otra instancia
                          está rotando en este momento).
        """
        redis_client = self._get_redis_client()

        if redis_client is not None:
            # Intentar adquirir el lock distribuido (SET NX EX)
            acquired = redis_client.set(
                _ROTATION_LOCK_KEY,
                "1",
                nx=True,
                ex=_ROTATION_LOCK_TTL,
            )
            if not acquired:
                raise RuntimeError(
                    "No se pudo adquirir el lock de rotación JWT. "
                    "Otra instancia está realizando la rotación en este momento. "
                    "Reintentar en unos segundos."
                )

        try:
            nueva_clave = secrets.token_hex(32)  # 64 caracteres hexadecimales

            # Archivar la clave actual como "previous"
            clave_actual = self._load_raw_secret(
                vault_name="jwt-secret-key",
                env_var="JWT_SECRET_KEY",
            )

            if clave_actual:
                self._store_secret(
                    vault_name="jwt-secret-key-previous",
                    env_var="JWT_SECRET_KEY_PREVIOUS",
                    value=clave_actual,
                )
                # Guardar el timestamp de la clave anterior para el grace period
                self._store_secret(
                    vault_name="jwt-secret-key-previous-created-at",
                    env_var="JWT_SECRET_KEY_PREVIOUS_CREATED_AT",
                    value=datetime.now(UTC).isoformat(),
                )

            # Almacenar la nueva clave activa
            self._store_secret(
                vault_name="jwt-secret-key",
                env_var="JWT_SECRET_KEY",
                value=nueva_clave,
            )

            # Actualizar el timestamp de la clave activa
            self._store_secret(
                vault_name="jwt-secret-key-created-at",
                env_var="JWT_SECRET_KEY_CREATED_AT",
                value=datetime.now(UTC).isoformat(),
            )

            # Registrar en el audit log
            self._log_rotation_audit(nueva_clave)

            logger.info(
                "Rotación de clave JWT completada. Nueva versión generada a las %s UTC.",
                datetime.now(UTC).isoformat(),
            )

            return nueva_clave

        finally:
            # Liberar el lock Redis si fue adquirido
            if redis_client is not None:
                redis_client.delete(_ROTATION_LOCK_KEY)

    # ------------------------------------------------------------------
    # Métodos privados de soporte
    # ------------------------------------------------------------------

    def _load_raw_secret(self, vault_name: str, env_var: str) -> str | None:
        """
        Intenta cargar un secreto desde Key Vault o variable de entorno.

        Returns:
            El valor del secreto, o ``None`` si no está disponible en ninguna fuente.
        """
        if self.use_key_vault and self.client is not None:
            try:
                secret = self.client.get_secret(vault_name)
                return secret.value or None
            except ResourceNotFoundError:
                pass
            except Exception as exc:
                logger.warning(
                    "Error al leer '%s' desde Key Vault: %s", vault_name, exc
                )

        value = os.getenv(env_var)
        return value if value else None

    def _store_secret(self, vault_name: str, env_var: str, value: str) -> None:
        """
        Almacena un secreto en Key Vault o, como fallback, en la variable de entorno
        del proceso actual (útil en entornos de desarrollo/test).

        En producción con Key Vault configurado, el secreto se persiste en el vault.
        Sin Key Vault, se actualiza la variable de entorno del proceso (no persiste
        entre reinicios — en producción siempre debe usarse Key Vault).
        """
        if self.use_key_vault and self.client is not None:
            try:
                self.client.set_secret(vault_name, value)
                return
            except Exception as exc:
                logger.error(
                    "Error al escribir '%s' en Key Vault: %s. "
                    "Usando variable de entorno como fallback.",
                    vault_name,
                    exc,
                )

        # Fallback: actualizar variable de entorno del proceso
        os.environ[env_var] = value

    def _load_active_key_timestamp(self) -> datetime | None:
        """
        Carga el timestamp de creación de la clave JWT activa.

        Returns:
            Datetime UTC de creación, o ``None`` si no está disponible.
        """
        raw = self._load_raw_secret(
            vault_name="jwt-secret-key-created-at",
            env_var="JWT_SECRET_KEY_CREATED_AT",
        )
        return self._parse_iso_datetime(raw)

    def _load_previous_key_timestamp(self) -> datetime | None:
        """
        Carga el timestamp de creación de la clave JWT anterior.

        Returns:
            Datetime UTC de creación, o ``None`` si no está disponible.
        """
        raw = self._load_raw_secret(
            vault_name="jwt-secret-key-previous-created-at",
            env_var="JWT_SECRET_KEY_PREVIOUS_CREATED_AT",
        )
        return self._parse_iso_datetime(raw)

    def _is_within_grace_period(self, created_at: datetime | None) -> bool:
        """
        Determina si una clave está dentro del período de gracia de 7 días.

        Si no hay información de fecha (``created_at`` es ``None``), retorna ``True``
        para ser conservador y no invalidar sesiones activas.

        Args:
            created_at: Momento de creación de la clave en UTC, o ``None``.

        Returns:
            ``True`` si la clave debe incluirse para verificación.
        """
        if created_at is None:
            # Sin timestamp, incluir siempre (conservador)
            return True

        age = datetime.now(UTC) - created_at
        return age <= timedelta(days=_GRACE_PERIOD_DAYS)

    @staticmethod
    def _parse_iso_datetime(value: str | None) -> datetime | None:
        """
        Parsea un string ISO 8601 a datetime con timezone UTC.

        Returns:
            Datetime UTC, o ``None`` si el valor es inválido o ausente.
        """
        if not value:
            return None
        try:
            dt = datetime.fromisoformat(value)
            # Asegurar que tiene timezone UTC
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=UTC)
            return dt
        except (ValueError, TypeError):
            logger.warning("No se pudo parsear el timestamp de clave JWT: %r", value)
            return None

    def _get_redis_client(self):
        """
        Obtiene un cliente Redis síncrono para el lock de rotación.

        Returns:
            Cliente Redis, o ``None`` si Redis no está disponible
            (en ese caso la rotación procede sin lock distribuido).
        """
        try:
            import redis as redis_lib

            redis_url = os.getenv("REDIS_URL", "redis://redis:6379")
            client = redis_lib.from_url(redis_url, decode_responses=True)
            # Verificar conectividad
            client.ping()
            return client
        except Exception as exc:
            logger.warning(
                "Redis no disponible para lock de rotación JWT (%s). "
                "Procediendo sin lock distribuido.",
                exc,
            )
            return None

    def _log_rotation_audit(self, nueva_clave: str) -> None:
        """
        Registra el evento de rotación JWT en el audit log.

        Usa una sesión de BD independiente para garantizar que el registro
        se persiste incluso si la transacción principal falla.

        Args:
            nueva_clave: La nueva clave generada (solo se registra su longitud,
                         nunca el valor en texto plano).
        """
        try:
            from app.configuracion.base_datos import SessionLocal
            from app.modelos.audit_log import AuditAction, AuditLog

            db = SessionLocal()
            try:
                entry = AuditLog(
                    user_id=None,  # Acción del sistema, no de un usuario
                    action=AuditAction.JWT_KEY_ROTATION,
                    resource_type="jwt_key",
                    resource_id=None,
                    ip_address="127.0.0.1",  # Acción interna del sistema
                    user_agent="SecretsManager/rotate_jwt_key",
                    details={
                        "event": "jwt_key_rotation",
                        "key_length": len(nueva_clave),
                        "timestamp": datetime.now(UTC).isoformat(),
                    },
                )
                db.add(entry)
                db.commit()
            finally:
                db.close()
        except Exception as exc:
            # El fallo del audit log no debe interrumpir la rotación
            logger.error(
                "No se pudo registrar la rotación JWT en el audit log: %s", exc
            )
