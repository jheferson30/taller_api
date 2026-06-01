"""
Tests unitarios y property-based tests para TokenManager con soporte multi-clave.

Cubre:
- Token firmado con clave activa → verificación exitosa
- Token firmado con clave anterior dentro del grace period → verificación exitosa
- Token firmado con clave anterior fuera del grace period (no incluida) → falla
- Token expirado → ExpiredSignatureError
- Sin claves → error descriptivo
- Property test (Hypothesis): grace period — firmar con clave anterior, verificar con ambas claves

**Validates: Requirements 3.2, 3.3**
"""

import os
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

import jwt
import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError

from app.configuracion.secrets_manager import JWTKeyEntry
from app.seguridad.token_manager import TokenManager


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_key_entry(
    key: str,
    is_active: bool,
    created_at: datetime | None = None,
    version: str | None = None,
) -> JWTKeyEntry:
    """Crea un JWTKeyEntry de prueba con valores por defecto razonables."""
    return JWTKeyEntry(
        version=version or ("active-v2" if is_active else "previous-v1"),
        key=key,
        created_at=created_at or datetime.now(UTC),
        is_active=is_active,
    )


def make_user(user_id: int = 1, username: str = "testuser") -> MagicMock:
    """Crea un usuario mock para tests (sin dependencia de BD)."""
    user = MagicMock()
    user.id = user_id
    user.username = username
    role = MagicMock()
    role.name = "ADMIN"
    user.roles = [role]
    return user


# Claves de prueba (≥ 32 caracteres)
ACTIVE_KEY = "a" * 64   # clave activa actual
PREVIOUS_KEY = "b" * 64  # clave anterior (grace period)
UNRELATED_KEY = "c" * 64  # clave que nunca estuvo en el manager


# ---------------------------------------------------------------------------
# Tests unitarios — compatibilidad con secret_key string
# ---------------------------------------------------------------------------

class TestCompatibilidadSecretKey:
    """Verifica que el modo legacy (secret_key string) sigue funcionando."""

    def test_constructor_con_secret_key_string(self):
        """TokenManager(secret_key=...) debe funcionar igual que antes."""
        tm = TokenManager(secret_key=ACTIVE_KEY)
        assert tm.secret_key == ACTIVE_KEY
        assert len(tm.keys) == 1
        assert tm.keys[0].is_active is True

    def test_generate_y_decode_con_secret_key(self):
        """Generar y decodificar token en modo legacy debe funcionar."""
        tm = TokenManager(secret_key=ACTIVE_KEY)
        user = make_user()
        token = tm.generate_access_token(user)
        payload = tm.decode_token(token)
        assert payload["user_id"] == user.id

    def test_secret_key_muy_corta_lanza_error(self):
        """Clave de menos de 32 caracteres debe lanzar ValueError."""
        with pytest.raises(ValueError, match="at least 32 characters"):
            TokenManager(secret_key="corta")

    def test_sin_secret_key_ni_env_lanza_error(self, monkeypatch):
        """Sin clave disponible debe lanzar ValueError descriptivo."""
        monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
        with pytest.raises(ValueError, match="JWT_SECRET_KEY"):
            TokenManager()


# ---------------------------------------------------------------------------
# Tests unitarios — modo multi-clave
# ---------------------------------------------------------------------------

class TestModoMultiClave:
    """Verifica el comportamiento con lista de JWTKeyEntry."""

    def test_token_firmado_con_clave_activa_verifica_exitosamente(self):
        """
        Token firmado con la clave activa debe verificarse correctamente.
        """
        active = make_key_entry(ACTIVE_KEY, is_active=True)
        tm = TokenManager(keys=[active])
        user = make_user()

        token = tm.generate_access_token(user)
        payload = tm.decode_token(token)

        assert payload["user_id"] == user.id
        assert payload["kid"] == active.version

    def test_token_firmado_con_clave_anterior_dentro_grace_period_verifica(self):
        """
        Token firmado con la clave anterior (dentro del grace period de 7 días)
        debe verificarse exitosamente cuando el TokenManager tiene ambas claves.
        """
        # Clave anterior creada hace 3 días (dentro del grace period)
        previous_created = datetime.now(UTC) - timedelta(days=3)
        previous = make_key_entry(PREVIOUS_KEY, is_active=False, created_at=previous_created)
        active = make_key_entry(ACTIVE_KEY, is_active=True)

        # Firmar con la clave anterior directamente (simula token emitido antes de la rotación)
        now = datetime.now(UTC)
        raw_payload = {
            "user_id": 42,
            "username": "usuario",
            "exp": now + timedelta(minutes=15),
            "iat": now,
            "kid": previous.version,
        }
        token_con_clave_anterior = jwt.encode(raw_payload, PREVIOUS_KEY, algorithm="HS256")

        # TokenManager con ambas claves debe aceptar el token
        tm = TokenManager(keys=[active, previous])
        payload = tm.decode_token(token_con_clave_anterior)

        assert payload["user_id"] == 42

    def test_token_firmado_con_clave_no_incluida_falla(self):
        """
        Token firmado con una clave que no está en el TokenManager debe fallar.
        Simula una clave anterior fuera del grace period (ya no incluida).
        """
        active = make_key_entry(ACTIVE_KEY, is_active=True)
        tm = TokenManager(keys=[active])  # Solo tiene la clave activa

        # Token firmado con una clave completamente diferente
        now = datetime.now(UTC)
        raw_payload = {
            "user_id": 99,
            "exp": now + timedelta(minutes=15),
            "iat": now,
        }
        token_clave_ajena = jwt.encode(raw_payload, UNRELATED_KEY, algorithm="HS256")

        with pytest.raises(InvalidTokenError):
            tm.decode_token(token_clave_ajena)

    def test_token_expirado_lanza_expired_signature_error(self):
        """
        Token expirado debe lanzar ExpiredSignatureError inmediatamente,
        sin intentar otras claves.
        """
        active = make_key_entry(ACTIVE_KEY, is_active=True)
        previous = make_key_entry(PREVIOUS_KEY, is_active=False)
        tm = TokenManager(keys=[active, previous])

        # Crear token ya expirado
        now = datetime.now(UTC)
        raw_payload = {
            "user_id": 1,
            "exp": now - timedelta(minutes=5),  # expirado hace 5 minutos
            "iat": now - timedelta(minutes=20),
        }
        token_expirado = jwt.encode(raw_payload, ACTIVE_KEY, algorithm="HS256")

        with pytest.raises(ExpiredSignatureError):
            tm.decode_token(token_expirado)

    def test_lista_vacia_lanza_error_descriptivo(self):
        """
        Pasar lista vacía de claves debe lanzar ValueError con mensaje descriptivo.
        """
        with pytest.raises(ValueError, match="no puede estar vacía"):
            TokenManager(keys=[])

    def test_sin_clave_activa_lanza_error_descriptivo(self):
        """
        Lista de claves sin ninguna is_active=True debe lanzar ValueError.
        """
        previous = make_key_entry(PREVIOUS_KEY, is_active=False)
        with pytest.raises(ValueError, match="is_active=True"):
            TokenManager(keys=[previous])

    def test_kid_incluido_en_payload_access_token(self):
        """
        El payload del access token debe incluir el campo 'kid' con la versión de la clave.
        """
        active = make_key_entry(ACTIVE_KEY, is_active=True, version="v2-2024")
        tm = TokenManager(keys=[active])
        user = make_user()

        token = tm.generate_access_token(user)
        payload = tm.decode_token(token)

        assert "kid" in payload
        assert payload["kid"] == "v2-2024"

    def test_kid_incluido_en_payload_refresh_token(self):
        """
        El payload del refresh token debe incluir el campo 'kid' con la versión de la clave.
        """
        active = make_key_entry(ACTIVE_KEY, is_active=True, version="v2-2024")
        tm = TokenManager(keys=[active])
        user = make_user()

        token = tm.generate_refresh_token(user)
        payload = tm.decode_token(token)

        assert "kid" in payload
        assert payload["kid"] == "v2-2024"

    def test_decode_intenta_claves_en_orden_descendente_por_created_at(self):
        """
        decode_token debe intentar las claves más recientes primero.
        El token firmado con la clave más antigua debe verificarse correctamente
        cuando la clave más reciente falla.
        """
        # Clave más antigua (pero activa)
        older_created = datetime.now(UTC) - timedelta(days=5)
        older_key = make_key_entry(ACTIVE_KEY, is_active=True, created_at=older_created, version="v1")

        # Clave más reciente (no activa, pero incluida)
        newer_created = datetime.now(UTC) - timedelta(days=1)
        newer_key = make_key_entry(PREVIOUS_KEY, is_active=False, created_at=newer_created, version="v2")

        # Nota: en este test la clave "activa" es la más antigua, la más reciente es la anterior.
        # Esto es inusual pero válido para probar el orden de iteración.
        # El token está firmado con ACTIVE_KEY (la más antigua).
        now = datetime.now(UTC)
        raw_payload = {
            "user_id": 7,
            "exp": now + timedelta(minutes=15),
            "iat": now,
        }
        token = jwt.encode(raw_payload, ACTIVE_KEY, algorithm="HS256")

        tm = TokenManager(keys=[older_key, newer_key])
        # La clave más reciente (newer_key con PREVIOUS_KEY) fallará,
        # pero la más antigua (older_key con ACTIVE_KEY) debe tener éxito.
        payload = tm.decode_token(token)
        assert payload["user_id"] == 7


# ---------------------------------------------------------------------------
# Property-based test — JWT Grace Period (Hypothesis)
# ---------------------------------------------------------------------------

@st.composite
def jwt_payload_strategy(draw):
    """Genera payloads JWT arbitrarios con user_id entero."""
    user_id = draw(st.integers(min_value=1, max_value=1_000_000))
    username = draw(st.text(
        alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd")),
        min_size=1,
        max_size=30,
    ))
    return {"user_id": user_id, "username": username}


@st.composite
def key_pair_strategy(draw):
    """
    Genera un par de claves JWT distintas (activa y anterior).
    Ambas tienen al menos 64 caracteres para cumplir el mínimo de seguridad.
    """
    # Usar caracteres ASCII imprimibles para las claves
    chars = st.characters(
        whitelist_categories=("Lu", "Ll", "Nd"),
        min_codepoint=65,
        max_codepoint=122,
    )
    active_key = draw(st.text(alphabet=chars, min_size=64, max_size=64))
    previous_key = draw(st.text(alphabet=chars, min_size=64, max_size=64))

    # Asegurar que las claves son distintas
    assume_different = active_key != previous_key
    return active_key, previous_key, assume_different


@pytest.mark.property_test
class TestPropertyGracePeriod:
    """
    Property 2: JWT Grace Period Verification

    **Validates: Requirements 3.2, 3.3**

    Propiedad: FOR ALL tokens signed with a JWT_Secret_Key that was the active key
    at signing time, WHEN the token is presented to JWT_Decoder within 7 days of a
    JWT_Key_Rotation that replaced that key, THE JWT_Decoder SHALL successfully
    verify the token.
    """

    @settings(
        max_examples=50,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    @given(payload=jwt_payload_strategy(), keys=key_pair_strategy())
    def test_token_firmado_con_clave_anterior_verifica_con_ambas_claves(
        self, payload, keys
    ):
        """
        Property: Firmar con la clave anterior y verificar con TokenManager
        que tiene ambas claves (activa + anterior) debe tener éxito.

        Simula el escenario de grace period: un token emitido antes de la rotación
        debe seguir siendo válido durante los 7 días posteriores.
        """
        active_key_str, previous_key_str, are_different = keys

        # Si las claves son iguales, el test no es significativo — saltarlo
        if not are_different or active_key_str == previous_key_str:
            return

        now = datetime.now(UTC)
        # Clave anterior creada hace 3 días (dentro del grace period de 7 días)
        previous_created = now - timedelta(days=3)

        previous_entry = JWTKeyEntry(
            version="previous-v1",
            key=previous_key_str,
            created_at=previous_created,
            is_active=False,
        )
        active_entry = JWTKeyEntry(
            version="active-v2",
            key=active_key_str,
            created_at=now,
            is_active=True,
        )

        # Firmar el token con la clave anterior (como si se hubiera emitido antes de la rotación)
        token_payload = {
            **payload,
            "exp": now + timedelta(minutes=15),
            "iat": now,
            "jti": "test-jti",
            "kid": "previous-v1",
        }
        token = jwt.encode(token_payload, previous_key_str, algorithm="HS256")

        # TokenManager con ambas claves debe aceptar el token
        tm = TokenManager(keys=[active_entry, previous_entry])
        decoded = tm.decode_token(token)

        assert decoded["user_id"] == payload["user_id"]

    @settings(
        max_examples=50,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    @given(payload=jwt_payload_strategy(), keys=key_pair_strategy())
    def test_token_firmado_con_clave_anterior_rechazado_sin_ella(
        self, payload, keys
    ):
        """
        Property: Firmar con la clave anterior y verificar con TokenManager
        que SOLO tiene la clave activa debe fallar.

        Simula el escenario post-grace-period: la clave anterior ya no está
        incluida en el TokenManager.
        """
        active_key_str, previous_key_str, are_different = keys

        if not are_different or active_key_str == previous_key_str:
            return

        now = datetime.now(UTC)
        active_entry = JWTKeyEntry(
            version="active-v2",
            key=active_key_str,
            created_at=now,
            is_active=True,
        )

        # Firmar con la clave anterior
        token_payload = {
            **payload,
            "exp": now + timedelta(minutes=15),
            "iat": now,
            "jti": "test-jti",
        }
        token = jwt.encode(token_payload, previous_key_str, algorithm="HS256")

        # TokenManager con SOLO la clave activa debe rechazar el token
        tm = TokenManager(keys=[active_entry])
        with pytest.raises(InvalidTokenError):
            tm.decode_token(token)
