"""
Tests unitarios y property-based tests para PIIEncryptor y EncryptedString.

Cubre:
- Round-trip: decrypt(encrypt(value)) == value para cualquier string
- IV único: el mismo plaintext cifrado dos veces produce ciphertexts distintos
- Corrupción de ciphertext → ValueError (fallo de autenticación AES-GCM)
- Clave maestra no disponible → RuntimeError al construir el encryptor
- EncryptedString TypeDecorator: process_bind_param y process_result_value
- is_encrypted: heurística de detección para migración

**Validates: Requirements 4.4, 4.5, 4.6, 4.7, 4.8**
**Properties: 1 (PII Round-Trip) y 4 (PII Unique Ciphertexts)**
"""

import base64
import os
from unittest.mock import MagicMock, patch

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from app.utils.pii_encryptor import EncryptedString, PIIEncryptor, _get_encryptor

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

TEST_MASTER_KEY = "clave-maestra-de-prueba-con-suficiente-longitud-para-hkdf-sha256"


@pytest.fixture
def encryptor() -> PIIEncryptor:
    """Instancia de PIIEncryptor con clave de prueba, sin SecretsManager real."""
    with patch.dict(os.environ, {"PII_MASTER_KEY": TEST_MASTER_KEY}):
        return PIIEncryptor(secrets_manager=None)


@pytest.fixture
def mock_secrets_manager() -> MagicMock:
    """SecretsManager mock que retorna la clave de prueba."""
    manager = MagicMock()
    manager.get_secret.return_value = TEST_MASTER_KEY
    return manager


# ---------------------------------------------------------------------------
# Tests unitarios — construcción
# ---------------------------------------------------------------------------

class TestConstruccion:
    """Verifica la inicialización del encryptor."""

    def test_construye_con_variable_de_entorno(self):
        """PIIEncryptor debe construirse correctamente con PII_MASTER_KEY en env."""
        with patch.dict(os.environ, {"PII_MASTER_KEY": TEST_MASTER_KEY}):
            enc = PIIEncryptor(secrets_manager=None)
        assert enc is not None

    def test_construye_con_secrets_manager(self, mock_secrets_manager):
        """PIIEncryptor debe construirse usando SecretsManager cuando se provee."""
        enc = PIIEncryptor(secrets_manager=mock_secrets_manager)
        assert enc is not None
        mock_secrets_manager.get_secret.assert_called_once_with(
            "pii-master-key", fallback_env_var="PII_MASTER_KEY"
        )

    def test_falla_sin_master_key(self, monkeypatch):
        """
        Sin PII_MASTER_KEY disponible, la construcción debe lanzar RuntimeError
        con mensaje descriptivo que identifica la clave faltante.
        """
        monkeypatch.delenv("PII_MASTER_KEY", raising=False)
        manager_sin_clave = MagicMock()
        manager_sin_clave.get_secret.side_effect = RuntimeError("Secret not found")

        with pytest.raises(RuntimeError, match="PII_MASTER_KEY"):
            PIIEncryptor(secrets_manager=manager_sin_clave)

    def test_falla_sin_master_key_ni_secrets_manager(self, monkeypatch):
        """Sin ninguna fuente de clave, debe lanzar RuntimeError."""
        monkeypatch.delenv("PII_MASTER_KEY", raising=False)
        with pytest.raises(RuntimeError, match="PII_MASTER_KEY"):
            PIIEncryptor(secrets_manager=None)


# ---------------------------------------------------------------------------
# Tests unitarios — encrypt / decrypt
# ---------------------------------------------------------------------------

class TestEncryptDecrypt:
    """Verifica el comportamiento de cifrado y descifrado."""

    def test_round_trip_nombre(self, encryptor):
        """Cifrar y descifrar un nombre debe retornar el valor original."""
        nombre = "Juan Pérez García"
        assert encryptor.decrypt(encryptor.encrypt(nombre)) == nombre

    def test_round_trip_telefono(self, encryptor):
        """Cifrar y descifrar un teléfono debe retornar el valor original."""
        telefono = "+57 300 123 4567"
        assert encryptor.decrypt(encryptor.encrypt(telefono)) == telefono

    def test_round_trip_email(self, encryptor):
        """Cifrar y descifrar un email debe retornar el valor original."""
        email = "usuario@ejemplo.com"
        assert encryptor.decrypt(encryptor.encrypt(email)) == email

    def test_round_trip_string_vacio(self, encryptor):
        """Un string vacío debe cifrarse y descifrarse correctamente."""
        assert encryptor.decrypt(encryptor.encrypt("")) == ""

    def test_round_trip_unicode(self, encryptor):
        """Strings con caracteres Unicode deben sobrevivir el round-trip."""
        valor = "María José Ñoño 中文 🔐"
        assert encryptor.decrypt(encryptor.encrypt(valor)) == valor

    def test_encrypt_retorna_string_base64(self, encryptor):
        """El ciphertext debe ser un string base64 válido."""
        ciphertext = encryptor.encrypt("test")
        # Verificar que es base64 válido
        decoded = base64.b64decode(ciphertext)
        assert len(decoded) > 0

    def test_encrypt_none_lanza_value_error(self, encryptor):
        """Cifrar None debe lanzar ValueError."""
        with pytest.raises(ValueError):
            encryptor.encrypt(None)

    def test_decrypt_none_lanza_value_error(self, encryptor):
        """Descifrar None debe lanzar ValueError."""
        with pytest.raises(ValueError):
            encryptor.decrypt(None)

    def test_iv_unico_por_operacion(self, encryptor):
        """
        El mismo plaintext cifrado dos veces debe producir ciphertexts distintos
        (IV único por operación garantiza esto).
        """
        valor = "mismo valor"
        c1 = encryptor.encrypt(valor)
        c2 = encryptor.encrypt(valor)
        assert c1 != c2

    def test_ambos_ciphertexts_decriptan_igual(self, encryptor):
        """
        Aunque los ciphertexts sean distintos, ambos deben descifrar al mismo plaintext.
        """
        valor = "mismo valor"
        c1 = encryptor.encrypt(valor)
        c2 = encryptor.encrypt(valor)
        assert encryptor.decrypt(c1) == valor
        assert encryptor.decrypt(c2) == valor


# ---------------------------------------------------------------------------
# Tests unitarios — corrupción y errores de autenticación
# ---------------------------------------------------------------------------

class TestCorrupcionYAutenticacion:
    """Verifica que la autenticación AES-GCM detecta corrupción."""

    def test_ciphertext_corrupto_lanza_value_error(self, encryptor):
        """
        Modificar cualquier byte del ciphertext debe causar ValueError
        (fallo de verificación del tag de autenticación AES-GCM).
        """
        ciphertext = encryptor.encrypt("dato sensible")
        raw = bytearray(base64.b64decode(ciphertext))

        # Corromper el último byte del ciphertext
        raw[-1] ^= 0xFF
        corrupto = base64.b64encode(bytes(raw)).decode("ascii")

        with pytest.raises(ValueError, match="autenticación"):
            encryptor.decrypt(corrupto)

    def test_tag_corrupto_lanza_value_error(self, encryptor):
        """
        Modificar el tag de autenticación (bytes 12-27) debe causar ValueError.
        """
        ciphertext = encryptor.encrypt("dato sensible")
        raw = bytearray(base64.b64decode(ciphertext))

        # Corromper el primer byte del tag (byte 12, justo después del IV)
        raw[12] ^= 0x01
        corrupto = base64.b64encode(bytes(raw)).decode("ascii")

        with pytest.raises(ValueError):
            encryptor.decrypt(corrupto)

    def test_iv_corrupto_lanza_value_error(self, encryptor):
        """
        Modificar el IV (primeros 12 bytes) debe causar ValueError.
        """
        ciphertext = encryptor.encrypt("dato sensible")
        raw = bytearray(base64.b64decode(ciphertext))

        # Corromper el primer byte del IV
        raw[0] ^= 0xFF
        corrupto = base64.b64encode(bytes(raw)).decode("ascii")

        with pytest.raises(ValueError):
            encryptor.decrypt(corrupto)

    def test_base64_invalido_lanza_value_error(self, encryptor):
        """Un string que no es base64 válido debe lanzar ValueError."""
        with pytest.raises(ValueError, match="base64"):
            encryptor.decrypt("esto no es base64 válido!!!")

    def test_ciphertext_demasiado_corto_lanza_value_error(self, encryptor):
        """Un ciphertext más corto que IV+TAG (28 bytes) debe lanzar ValueError."""
        # 10 bytes en base64 = 16 caracteres, claramente por debajo del mínimo de 28 bytes
        corto = base64.b64encode(b"x" * 10).decode("ascii")
        with pytest.raises(ValueError, match="corto"):
            encryptor.decrypt(corto)

    def test_clave_diferente_no_puede_descifrar(self):
        """
        Un encryptor con clave diferente no debe poder descifrar datos
        cifrados con otra clave.
        """
        with patch.dict(os.environ, {"PII_MASTER_KEY": "clave-uno-" + "a" * 50}):
            enc1 = PIIEncryptor(secrets_manager=None)

        with patch.dict(os.environ, {"PII_MASTER_KEY": "clave-dos-" + "b" * 50}):
            enc2 = PIIEncryptor(secrets_manager=None)

        ciphertext = enc1.encrypt("dato secreto")

        with pytest.raises(ValueError):
            enc2.decrypt(ciphertext)


# ---------------------------------------------------------------------------
# Tests unitarios — is_encrypted (heurística de migración)
# ---------------------------------------------------------------------------

class TestIsEncrypted:
    """Verifica la heurística de detección de valores ya cifrados."""

    def test_valor_cifrado_detectado_como_cifrado(self, encryptor):
        """Un valor cifrado por encrypt() debe ser detectado como cifrado."""
        ciphertext = encryptor.encrypt("Juan Pérez")
        assert encryptor.is_encrypted(ciphertext) is True

    def test_nombre_plaintext_no_detectado_como_cifrado(self, encryptor):
        """Un nombre en texto plano no debe ser detectado como cifrado."""
        assert encryptor.is_encrypted("Juan Pérez García") is False

    def test_telefono_plaintext_no_detectado_como_cifrado(self, encryptor):
        """Un teléfono en texto plano no debe ser detectado como cifrado."""
        assert encryptor.is_encrypted("+57 300 123 4567") is False

    def test_none_no_detectado_como_cifrado(self, encryptor):
        """None no debe ser detectado como cifrado."""
        assert encryptor.is_encrypted(None) is False

    def test_string_vacio_no_detectado_como_cifrado(self, encryptor):
        """String vacío no debe ser detectado como cifrado."""
        assert encryptor.is_encrypted("") is False

    def test_base64_corto_no_detectado_como_cifrado(self, encryptor):
        """Base64 válido pero con menos de 28 bytes decodificados no debe ser detectado como cifrado."""
        corto = base64.b64encode(b"abc").decode("ascii")  # 3 bytes < 28 bytes mínimo
        assert encryptor.is_encrypted(corto) is False


# ---------------------------------------------------------------------------
# Tests unitarios — EncryptedString TypeDecorator
# ---------------------------------------------------------------------------

class TestEncryptedStringTypeDecorator:
    """Verifica el TypeDecorator SQLAlchemy."""

    def test_process_bind_param_cifra_valor(self):
        """process_bind_param debe retornar el valor cifrado."""
        with patch.dict(os.environ, {"PII_MASTER_KEY": TEST_MASTER_KEY}):
            # Limpiar el singleton para que use la clave de prueba
            _get_encryptor.cache_clear()
            tipo = EncryptedString(500)
            resultado = tipo.process_bind_param("Juan Pérez", dialect=None)

        assert resultado is not None
        assert resultado != "Juan Pérez"
        # Debe ser base64 válido
        base64.b64decode(resultado)

    def test_process_bind_param_none_retorna_none(self):
        """process_bind_param con None debe retornar None (columnas nullable)."""
        with patch.dict(os.environ, {"PII_MASTER_KEY": TEST_MASTER_KEY}):
            _get_encryptor.cache_clear()
            tipo = EncryptedString(500)
            assert tipo.process_bind_param(None, dialect=None) is None

    def test_process_result_value_descifra_valor(self):
        """process_result_value debe retornar el plaintext original."""
        with patch.dict(os.environ, {"PII_MASTER_KEY": TEST_MASTER_KEY}):
            _get_encryptor.cache_clear()
            tipo = EncryptedString(500)
            ciphertext = tipo.process_bind_param("Juan Pérez", dialect=None)
            plaintext = tipo.process_result_value(ciphertext, dialect=None)

        assert plaintext == "Juan Pérez"

    def test_process_result_value_none_retorna_none(self):
        """process_result_value con None debe retornar None."""
        with patch.dict(os.environ, {"PII_MASTER_KEY": TEST_MASTER_KEY}):
            _get_encryptor.cache_clear()
            tipo = EncryptedString(500)
            assert tipo.process_result_value(None, dialect=None) is None

    def test_round_trip_completo_via_type_decorator(self):
        """El round-trip completo a través del TypeDecorator debe preservar el valor."""
        with patch.dict(os.environ, {"PII_MASTER_KEY": TEST_MASTER_KEY}):
            _get_encryptor.cache_clear()
            tipo = EncryptedString(500)
            original = "María José Ñoño"
            ciphertext = tipo.process_bind_param(original, dialect=None)
            recovered = tipo.process_result_value(ciphertext, dialect=None)

        assert recovered == original


# ---------------------------------------------------------------------------
# Property-based tests — Hypothesis
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=False)
def pii_encryptor_env():
    """Fixture que configura el entorno para property tests."""
    with patch.dict(os.environ, {"PII_MASTER_KEY": TEST_MASTER_KEY}):
        _get_encryptor.cache_clear()
        yield
    _get_encryptor.cache_clear()


# Estrategia para generar strings PII arbitrarios
pii_text_strategy = st.text(
    alphabet=st.characters(
        # Incluir letras, dígitos, espacios, puntuación y caracteres Unicode comunes
        blacklist_categories=("Cs",),  # Excluir surrogates (inválidos en UTF-8)
    ),
    min_size=1,
    max_size=500,
)


@pytest.mark.property_test
class TestPropertyPIIRoundTrip:
    """
    Property 1: PII Encryption Round-Trip

    FOR ALL non-empty string values representing PII, encrypting the value with
    PIIEncryptor and then decrypting the result SHALL produce a string equal to
    the original value.

    **Validates: Requirement 4.4, 4.5, 4.6 — Property 1**
    """

    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    @given(value=pii_text_strategy)
    def test_round_trip_pii(self, value, pii_encryptor_env):
        """
        Property: decrypt(encrypt(value)) == value para cualquier string PII.

        AES-256-GCM es cifrado autenticado: cualquier corrupción causa fallo
        de autenticación, nunca retorno silencioso de datos incorrectos.
        """
        with patch.dict(os.environ, {"PII_MASTER_KEY": TEST_MASTER_KEY}):
            enc = PIIEncryptor(secrets_manager=None)
            ciphertext = enc.encrypt(value)
            recovered = enc.decrypt(ciphertext)
        assert recovered == value, (
            f"Round-trip falló para value={value!r}: "
            f"se recuperó {recovered!r}"
        )


@pytest.mark.property_test
class TestPropertyPIIUniqueCiphertexts:
    """
    Property 4: PII Encryption Produces Unique Ciphertexts

    FOR ALL non-empty string values representing PII, encrypting the same value
    twice SHALL produce two different ciphertexts (due to unique IV per operation).

    **Validates: Requirement 4.7 — Property 4**
    """

    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    @given(value=pii_text_strategy)
    def test_ciphertexts_unicos(self, value, pii_encryptor_env):
        """
        Property: encrypt(value) != encrypt(value) — IV único por operación.

        Dos cifrados del mismo plaintext deben producir ciphertexts distintos,
        pero ambos deben descifrar al mismo valor original.
        """
        with patch.dict(os.environ, {"PII_MASTER_KEY": TEST_MASTER_KEY}):
            enc = PIIEncryptor(secrets_manager=None)
            c1 = enc.encrypt(value)
            c2 = enc.encrypt(value)

        assert c1 != c2, (
            f"Los ciphertexts son idénticos para value={value!r}. "
            "El IV no es único por operación."
        )

        with patch.dict(os.environ, {"PII_MASTER_KEY": TEST_MASTER_KEY}):
            enc = PIIEncryptor(secrets_manager=None)
            assert enc.decrypt(c1) == value
            assert enc.decrypt(c2) == value
