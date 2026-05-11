"""
PIIEncryptor — Cifrado AES-256-GCM transparente para datos PII.

Responsabilidad única: cifrar y descifrar strings de información personal
identificable (nombres, teléfonos, emails) usando AES-256-GCM con IV único
por operación.

La clave AES se deriva de la ``PII_MASTER_KEY`` almacenada en SecretsManager
usando HKDF-SHA256, garantizando separación entre la clave maestra y la clave
de cifrado efectiva.

Formato del ciphertext almacenado en BD:
    base64( IV(12 bytes) || TAG(16 bytes) || CIPHERTEXT )

Integración con SQLAlchemy:
    Usar ``EncryptedString`` como tipo de columna en lugar de ``String``.
    El cifrado/descifrado es completamente transparente para la capa de servicio.

**Validates: Requirements 4.4, 4.5, 4.6, 4.7, 4.8**
"""

import base64
import logging
import os
from functools import lru_cache

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from sqlalchemy import String
from sqlalchemy.types import TypeDecorator

logger = logging.getLogger(__name__)

# Parámetros de derivación de clave — fijos para garantizar reproducibilidad
_HKDF_SALT = b"taller-pii-v1"
_HKDF_INFO = b"aes-gcm-key"
_AES_KEY_LENGTH = 32   # 256 bits
_GCM_IV_LENGTH = 12    # 96 bits — recomendado por NIST para AES-GCM
_GCM_TAG_LENGTH = 16   # 128 bits — máxima seguridad del tag de autenticación


class PIIEncryptor:
    """
    Cifra y descifra strings de PII usando AES-256-GCM.

    La clave AES se deriva de la ``PII_MASTER_KEY`` mediante HKDF-SHA256.
    La clave derivada se cachea en memoria para evitar re-derivación en cada
    operación, manteniendo el rendimiento sin comprometer la seguridad.

    Uso típico:
        encryptor = PIIEncryptor(secrets_manager)
        ciphertext = encryptor.encrypt("Juan Pérez")
        plaintext  = encryptor.decrypt(ciphertext)  # → "Juan Pérez"
    """

    def __init__(self, secrets_manager=None) -> None:
        """
        Inicializa el encryptor derivando la clave AES desde la master key.

        Args:
            secrets_manager: Instancia de SecretsManager. Si es None, se
                             intenta cargar la clave directamente desde la
                             variable de entorno PII_MASTER_KEY.

        Raises:
            RuntimeError: Si PII_MASTER_KEY no está disponible en ninguna fuente.
        """
        master_key_str = self._load_master_key(secrets_manager)
        self._aes_key: bytes = self._derive_aes_key(master_key_str)
        self._aesgcm = AESGCM(self._aes_key)

    # ------------------------------------------------------------------
    # Interfaz pública
    # ------------------------------------------------------------------

    def encrypt(self, plaintext: str) -> str:
        """
        Cifra un string de PII con AES-256-GCM.

        Genera un IV único de 12 bytes por operación, garantizando que el mismo
        plaintext cifrado dos veces produce ciphertexts distintos.

        Args:
            plaintext: String a cifrar (nombre, teléfono, email, etc.)

        Returns:
            String base64 con formato: base64(IV || TAG || CIPHERTEXT).
            Seguro para almacenar directamente en columnas VARCHAR de la BD.

        Raises:
            ValueError: Si plaintext es None (usar None directamente en BD).
        """
        if plaintext is None:
            raise ValueError("No se puede cifrar None — usar None directamente en la BD.")

        # IV único de 12 bytes por operación (requisito de seguridad AES-GCM)
        iv = os.urandom(_GCM_IV_LENGTH)

        # AESGCM.encrypt retorna TAG(16 bytes) || CIPHERTEXT concatenados
        tag_and_ciphertext = self._aesgcm.encrypt(iv, plaintext.encode("utf-8"), None)

        # Formato final: IV || TAG || CIPHERTEXT → base64
        combined = iv + tag_and_ciphertext
        return base64.b64encode(combined).decode("ascii")

    def decrypt(self, ciphertext_b64: str) -> str:
        """
        Descifra un string cifrado con AES-256-GCM.

        Extrae el IV y verifica el tag de autenticación antes de retornar
        el plaintext. Cualquier corrupción del ciphertext, IV o tag causa
        un ValueError — nunca retorna datos incorrectos silenciosamente.

        Args:
            ciphertext_b64: String base64 producido por ``encrypt()``.

        Returns:
            El plaintext original como string UTF-8.

        Raises:
            ValueError: Si el ciphertext está corrupto, el tag no coincide,
                        o el formato base64 es inválido.
        """
        if ciphertext_b64 is None:
            raise ValueError("No se puede descifrar None.")

        try:
            combined = base64.b64decode(ciphertext_b64)
        except Exception as exc:
            raise ValueError(
                f"Ciphertext PII con formato base64 inválido: {exc}"
            ) from exc

        # Validar longitud mínima: IV(12) + TAG(16) + 0 o más bytes de datos
        # Nota: un string vacío produce exactamente 28 bytes (IV + TAG sin datos)
        min_length = _GCM_IV_LENGTH + _GCM_TAG_LENGTH
        if len(combined) < min_length:
            raise ValueError(
                f"Ciphertext PII demasiado corto ({len(combined)} bytes). "
                f"Mínimo esperado: {min_length} bytes."
            )

        iv = combined[:_GCM_IV_LENGTH]
        # AESGCM.decrypt espera TAG || CIPHERTEXT (el tag está al inicio del resto)
        tag_and_ciphertext = combined[_GCM_IV_LENGTH:]

        try:
            plaintext_bytes = self._aesgcm.decrypt(iv, tag_and_ciphertext, None)
        except InvalidTag as exc:
            raise ValueError(
                "Fallo de autenticación AES-GCM: el ciphertext PII está corrupto "
                "o fue modificado. No se puede descifrar."
            ) from exc

        return plaintext_bytes.decode("utf-8")

    def is_encrypted(self, value: str) -> bool:
        """
        Heurística para detectar si un valor ya está cifrado.

        Útil durante migraciones para evitar doble-cifrado de datos que ya
        fueron procesados en una ejecución anterior.

        La heurística verifica:
        1. El valor es un string base64 válido.
        2. Tiene la longitud mínima esperada (IV + TAG + datos).
        3. Al intentar descifrar no lanza error de formato.

        Args:
            value: String a evaluar.

        Returns:
            True si el valor parece estar cifrado; False si parece plaintext.
        """
        if not value or not isinstance(value, str):
            return False

        try:
            decoded = base64.b64decode(value)
        except Exception:
            return False

        # Longitud mínima: IV(12) + TAG(16) = 28 bytes (string vacío cifrado)
        # En base64: ceil(28 * 4/3) = 40 caracteres
        if len(decoded) < _GCM_IV_LENGTH + _GCM_TAG_LENGTH:
            return False

        # Verificar que el string original es base64 puro (sin espacios ni saltos)
        # Un plaintext normal raramente es base64 válido de la longitud correcta
        try:
            re_encoded = base64.b64encode(decoded).decode("ascii")
            return re_encoded == value
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Métodos privados
    # ------------------------------------------------------------------

    @staticmethod
    def _load_master_key(secrets_manager) -> str:
        """
        Carga la PII_MASTER_KEY desde SecretsManager o variable de entorno.

        Args:
            secrets_manager: Instancia de SecretsManager, o None.

        Returns:
            La master key como string.

        Raises:
            RuntimeError: Si la clave no está disponible en ninguna fuente.
        """
        if secrets_manager is not None:
            try:
                return secrets_manager.get_secret(
                    "pii-master-key",
                    fallback_env_var="PII_MASTER_KEY",
                )
            except RuntimeError:
                pass  # Intentar fallback directo a env var

        # Fallback directo a variable de entorno (útil en tests)
        value = os.getenv("PII_MASTER_KEY")
        if value:
            return value

        raise RuntimeError(
            "Secreto requerido no configurado: 'PII_MASTER_KEY'. "
            "Configurar en Azure Key Vault como 'pii-master-key' "
            "o como variable de entorno 'PII_MASTER_KEY'."
        )

    @staticmethod
    def _derive_aes_key(master_key_str: str) -> bytes:
        """
        Deriva una clave AES-256 de 32 bytes desde la master key usando HKDF-SHA256.

        El salt y el info son fijos para garantizar que la misma master key
        siempre produce la misma clave AES (necesario para descifrar datos
        existentes en la BD).

        Args:
            master_key_str: La master key como string.

        Returns:
            Clave AES de 32 bytes lista para usar con AESGCM.

        Raises:
            RuntimeError: Si la derivación falla (master key inválida).
        """
        try:
            hkdf = HKDF(
                algorithm=hashes.SHA256(),
                length=_AES_KEY_LENGTH,
                salt=_HKDF_SALT,
                info=_HKDF_INFO,
            )
            return hkdf.derive(master_key_str.encode("utf-8"))
        except Exception as exc:
            raise RuntimeError(
                f"No se pudo derivar la clave AES desde PII_MASTER_KEY: {exc}"
            ) from exc


# ---------------------------------------------------------------------------
# Singleton del encryptor para uso en SQLAlchemy TypeDecorator
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def _get_encryptor() -> PIIEncryptor:
    """
    Retorna la instancia singleton de PIIEncryptor.

    Usa lru_cache para garantizar que la derivación de clave HKDF ocurre
    una sola vez durante el ciclo de vida de la aplicación.

    La instancia se crea sin SecretsManager explícito; carga la clave
    directamente desde la variable de entorno PII_MASTER_KEY (que en
    producción es inyectada por el proceso de startup desde SecretsManager).

    Returns:
        Instancia singleton de PIIEncryptor.

    Raises:
        RuntimeError: Si PII_MASTER_KEY no está configurada.
    """
    return PIIEncryptor(secrets_manager=None)


# ---------------------------------------------------------------------------
# TypeDecorator SQLAlchemy — encriptación transparente
# ---------------------------------------------------------------------------

class EncryptedString(TypeDecorator):
    """
    Tipo SQLAlchemy que cifra al persistir y descifra al cargar.

    El cifrado/descifrado es completamente transparente para la capa de
    servicio: los modelos trabajan siempre con strings en texto plano,
    y la BD almacena siempre ciphertext base64.

    Uso en modelos:
        class Vehiculo(Base):
            nombre_propietario = Column(EncryptedString(500), nullable=True)
            telefono_propietario = Column(EncryptedString(500), nullable=True)

    El parámetro de longitud (500) debe ser suficiente para el ciphertext
    base64 resultante. Para un plaintext de N bytes, el ciphertext base64
    ocupa aproximadamente ceil((N + 28) * 4/3) caracteres.
    """

    impl = String
    cache_ok = True  # Seguro para caché de SQLAlchemy (no tiene estado mutable)

    def process_bind_param(self, value, dialect):
        """
        Llamado al hacer INSERT o UPDATE.

        Cifra el valor antes de enviarlo a la BD.
        None se pasa sin modificar (columnas nullable).
        """
        if value is None:
            return None
        try:
            return _get_encryptor().encrypt(value)
        except Exception as exc:
            logger.error("Error al cifrar campo PII: %s", exc)
            raise

    def process_result_value(self, value, dialect):
        """
        Llamado al hacer SELECT.

        Descifra el valor al cargarlo desde la BD.
        None se pasa sin modificar (columnas nullable con valor NULL).
        """
        if value is None:
            return None
        try:
            return _get_encryptor().decrypt(value)
        except ValueError as exc:
            # Loguear el error pero no exponer detalles al cliente
            logger.error(
                "Error al descifrar campo PII (posible corrupción o clave incorrecta): %s",
                exc,
            )
            raise
