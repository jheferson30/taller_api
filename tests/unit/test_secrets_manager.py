"""
Unit tests for SecretsManager class.

Tests cover:
- Key Vault retrieval with mocked Azure SDK
- Fallback to environment variables
- Error handling for missing secrets
"""
import os
import pytest
from unittest.mock import Mock, patch, MagicMock
from azure.core.exceptions import ResourceNotFoundError
from app.configuracion.secrets_manager import SecretsManager


class TestSecretsManagerKeyVault:
    """Tests for SecretsManager with Azure Key Vault enabled."""
    
    @patch('app.configuracion.secrets_manager.DefaultAzureCredential')
    @patch('app.configuracion.secrets_manager.SecretClient')
    @patch.dict('os.environ', {'AZURE_KEY_VAULT_URL': 'https://test-vault.vault.azure.net/'})
    def test_get_secret_from_key_vault_success(self, mock_secret_client, mock_credential):
        """Test successful secret retrieval from Key Vault."""
        # Arrange
        mock_secret = Mock()
        mock_secret.value = "secret_value_from_vault"
        mock_client_instance = Mock()
        mock_client_instance.get_secret.return_value = mock_secret
        mock_secret_client.return_value = mock_client_instance
        
        # Act
        manager = SecretsManager()
        result = manager.get_secret("database-password")
        
        # Assert
        assert result == "secret_value_from_vault"
        mock_client_instance.get_secret.assert_called_once_with("database-password")
        assert manager.use_key_vault is True
    
    @patch('app.configuracion.secrets_manager.DefaultAzureCredential')
    @patch('app.configuracion.secrets_manager.SecretClient')
    @patch.dict('os.environ', {
        'AZURE_KEY_VAULT_URL': 'https://test-vault.vault.azure.net/',
        'DATABASE_PASSWORD': 'fallback_password'
    })
    def test_get_secret_key_vault_not_found_fallback_to_env(self, mock_secret_client, mock_credential):
        """Test fallback to environment variable when secret not found in Key Vault."""
        # Arrange
        mock_client_instance = Mock()
        mock_client_instance.get_secret.side_effect = ResourceNotFoundError("Secret not found")
        mock_secret_client.return_value = mock_client_instance
        
        # Act
        manager = SecretsManager()
        result = manager.get_secret("database-password", fallback_env_var="DATABASE_PASSWORD")
        
        # Assert
        assert result == "fallback_password"
        mock_client_instance.get_secret.assert_called_once_with("database-password")
    
    @patch('app.configuracion.secrets_manager.DefaultAzureCredential')
    @patch('app.configuracion.secrets_manager.SecretClient')
    @patch.dict('os.environ', {'AZURE_KEY_VAULT_URL': 'https://test-vault.vault.azure.net/'})
    def test_get_secret_key_vault_not_found_no_fallback_raises_error(self, mock_secret_client, mock_credential):
        """Test error raised when secret not found in Key Vault and no fallback provided."""
        # Arrange
        mock_client_instance = Mock()
        mock_client_instance.get_secret.side_effect = ResourceNotFoundError("Secret not found")
        mock_secret_client.return_value = mock_client_instance
        
        # Act & Assert
        manager = SecretsManager()
        with pytest.raises(RuntimeError, match="Secret 'jwt-secret-key' not found in Key Vault"):
            manager.get_secret("jwt-secret-key")
    
    @patch('app.configuracion.secrets_manager.DefaultAzureCredential')
    @patch('app.configuracion.secrets_manager.SecretClient')
    @patch.dict('os.environ', {'AZURE_KEY_VAULT_URL': 'https://test-vault.vault.azure.net/'}, clear=True)
    def test_get_secret_key_vault_not_found_fallback_env_missing_raises_error(
        self, mock_secret_client, mock_credential
    ):
        """Test error raised when secret not found in Key Vault and fallback env var is missing."""
        # Arrange
        mock_client_instance = Mock()
        mock_client_instance.get_secret.side_effect = ResourceNotFoundError("Secret not found")
        mock_secret_client.return_value = mock_client_instance
        
        # Act & Assert
        manager = SecretsManager()
        with pytest.raises(RuntimeError, match="Secret 'admin-password' not found in Key Vault"):
            manager.get_secret("admin-password", fallback_env_var="ADMIN_PASSWORD")


class TestSecretsManagerEnvironmentVariables:
    """Tests for SecretsManager with environment variables only (no Key Vault)."""
    
    @patch.dict('os.environ', {'DATABASE_PASSWORD': 'env_password_123'}, clear=True)
    def test_get_secret_from_env_var_success(self):
        """Test successful secret retrieval from environment variable when Key Vault not configured."""
        # Act
        manager = SecretsManager()
        result = manager.get_secret("database-password", fallback_env_var="DATABASE_PASSWORD")
        
        # Assert
        assert result == "env_password_123"
        assert manager.use_key_vault is False
        assert manager.client is None
    
    @patch.dict('os.environ', {}, clear=True)
    def test_get_secret_env_var_missing_raises_error(self):
        """Test error raised when environment variable is missing."""
        # Act & Assert
        manager = SecretsManager()
        with pytest.raises(RuntimeError, match="Secret 'jwt-secret' not configured"):
            manager.get_secret("jwt-secret", fallback_env_var="JWT_SECRET_KEY")
    
    @patch.dict('os.environ', {}, clear=True)
    def test_get_secret_no_fallback_raises_error(self):
        """Test error raised when no fallback provided and Key Vault not configured."""
        # Act & Assert
        manager = SecretsManager()
        with pytest.raises(RuntimeError, match="Secret 'some-secret' not configured"):
            manager.get_secret("some-secret")
    
    @patch.dict('os.environ', {
        'JWT_SECRET_KEY': 'jwt_secret_value',
        'DATABASE_PASSWORD': 'db_password_value',
        'ADMIN_PASSWORD': 'admin_password_value'
    }, clear=True)
    def test_get_multiple_secrets_from_env_vars(self):
        """Test retrieving multiple secrets from environment variables."""
        # Act
        manager = SecretsManager()
        jwt_secret = manager.get_secret("jwt-secret-key", fallback_env_var="JWT_SECRET_KEY")
        db_password = manager.get_secret("database-password", fallback_env_var="DATABASE_PASSWORD")
        admin_password = manager.get_secret("admin-password", fallback_env_var="ADMIN_PASSWORD")
        
        # Assert
        assert jwt_secret == "jwt_secret_value"
        assert db_password == "db_password_value"
        assert admin_password == "admin_password_value"


class TestSecretsManagerInitialization:
    """Tests for SecretsManager initialization."""
    
    @patch('app.configuracion.secrets_manager.DefaultAzureCredential')
    @patch('app.configuracion.secrets_manager.SecretClient')
    @patch.dict('os.environ', {'AZURE_KEY_VAULT_URL': 'https://test-vault.vault.azure.net/'})
    def test_initialization_with_key_vault_url(self, mock_secret_client, mock_credential):
        """Test SecretsManager initializes with Key Vault when URL is provided."""
        # Act
        manager = SecretsManager()
        
        # Assert
        assert manager.use_key_vault is True
        assert manager.vault_url == 'https://test-vault.vault.azure.net/'
        mock_credential.assert_called_once()
        mock_secret_client.assert_called_once_with(
            vault_url='https://test-vault.vault.azure.net/',
            credential=mock_credential.return_value
        )
    
    @patch.dict('os.environ', {}, clear=True)
    def test_initialization_without_key_vault_url(self):
        """Test SecretsManager initializes without Key Vault when URL is not provided."""
        # Act
        manager = SecretsManager()
        
        # Assert
        assert manager.use_key_vault is False
        assert manager.vault_url is None
        assert manager.client is None


# ---------------------------------------------------------------------------
# Tests para la funcionalidad multi-clave JWT (Task 4)
# ---------------------------------------------------------------------------

from datetime import UTC, datetime, timedelta
from unittest.mock import patch

from app.configuracion.secrets_manager import JWTKeyEntry


class TestJWTKeyEntry:
    """Tests para el dataclass JWTKeyEntry."""

    def test_jwt_key_entry_fields(self):
        """JWTKeyEntry debe tener todos los campos requeridos con los tipos correctos."""
        now = datetime.now(UTC)
        entry = JWTKeyEntry(
            version="550e8400-e29b-41d4-a716-446655440000",
            key="a" * 64,
            created_at=now,
            is_active=True,
        )

        assert entry.version == "550e8400-e29b-41d4-a716-446655440000"
        assert entry.key == "a" * 64
        assert entry.created_at == now
        assert entry.is_active is True

    def test_jwt_key_entry_inactive(self):
        """JWTKeyEntry con is_active=False representa la clave anterior."""
        entry = JWTKeyEntry(
            version="v-prev",
            key="b" * 64,
            created_at=datetime.now(UTC),
            is_active=False,
        )
        assert entry.is_active is False


class TestGetJwtKeys:
    """Tests para SecretsManager.get_jwt_keys()."""

    @patch.dict(
        "os.environ",
        {"JWT_SECRET_KEY": "x" * 64},
        clear=True,
    )
    def test_returns_active_key_only_when_no_previous(self):
        """Cuando solo hay clave activa, retorna lista con un elemento is_active=True."""
        manager = SecretsManager()
        keys = manager.get_jwt_keys()

        assert len(keys) == 1
        assert keys[0].is_active is True
        assert keys[0].key == "x" * 64

    @patch.dict(
        "os.environ",
        {
            "JWT_SECRET_KEY": "a" * 64,
            "JWT_SECRET_KEY_PREVIOUS": "b" * 64,
        },
        clear=True,
    )
    def test_includes_previous_key_without_timestamp(self):
        """Sin timestamp de la clave anterior, se incluye siempre (comportamiento conservador)."""
        manager = SecretsManager()
        keys = manager.get_jwt_keys()

        assert len(keys) == 2
        active = [k for k in keys if k.is_active]
        previous = [k for k in keys if not k.is_active]
        assert len(active) == 1
        assert len(previous) == 1
        assert active[0].key == "a" * 64
        assert previous[0].key == "b" * 64

    @patch.dict(
        "os.environ",
        {
            "JWT_SECRET_KEY": "a" * 64,
            "JWT_SECRET_KEY_PREVIOUS": "b" * 64,
            # Clave anterior creada hace 3 días → dentro del grace period
            "JWT_SECRET_KEY_PREVIOUS_CREATED_AT": (
                datetime.now(UTC) - timedelta(days=3)
            ).isoformat(),
        },
        clear=True,
    )
    def test_includes_previous_key_within_grace_period(self):
        """La clave anterior se incluye si está dentro del grace period de 7 días."""
        manager = SecretsManager()
        keys = manager.get_jwt_keys()

        assert len(keys) == 2
        previous_keys = [k for k in keys if not k.is_active]
        assert len(previous_keys) == 1
        assert previous_keys[0].key == "b" * 64

    @patch.dict(
        "os.environ",
        {
            "JWT_SECRET_KEY": "a" * 64,
            "JWT_SECRET_KEY_PREVIOUS": "b" * 64,
            # Clave anterior creada hace 10 días → fuera del grace period
            "JWT_SECRET_KEY_PREVIOUS_CREATED_AT": (
                datetime.now(UTC) - timedelta(days=10)
            ).isoformat(),
        },
        clear=True,
    )
    def test_excludes_previous_key_outside_grace_period(self):
        """La clave anterior se descarta si superó el grace period de 7 días."""
        manager = SecretsManager()
        keys = manager.get_jwt_keys()

        assert len(keys) == 1
        assert keys[0].is_active is True

    @patch.dict("os.environ", {}, clear=True)
    def test_raises_runtime_error_when_no_active_key(self):
        """Sin clave activa disponible, debe lanzar RuntimeError descriptivo."""
        manager = SecretsManager()

        with pytest.raises(RuntimeError, match="JWT_SECRET_KEY"):
            manager.get_jwt_keys()

    @patch.dict(
        "os.environ",
        {"JWT_SECRET_KEY": "z" * 64},
        clear=True,
    )
    def test_active_key_has_uuid_version(self):
        """La clave activa debe tener un version UUID v4 válido."""
        import re

        manager = SecretsManager()
        keys = manager.get_jwt_keys()

        uuid_pattern = re.compile(
            r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
            re.IGNORECASE,
        )
        assert uuid_pattern.match(keys[0].version), (
            f"version '{keys[0].version}' no es un UUID v4 válido"
        )


class TestCheckRotationNeeded:
    """Tests para SecretsManager.check_rotation_needed()."""

    @patch.dict("os.environ", {}, clear=True)
    def test_returns_false_when_no_timestamp(self):
        """Sin información de fecha, retorna False (conservador)."""
        manager = SecretsManager()
        assert manager.check_rotation_needed() is False

    @patch.dict(
        "os.environ",
        {
            # Clave creada hace 91 días → necesita rotación
            "JWT_SECRET_KEY_CREATED_AT": (
                datetime.now(UTC) - timedelta(days=91)
            ).isoformat(),
        },
        clear=True,
    )
    def test_returns_true_when_key_older_than_90_days(self):
        """Retorna True si la clave activa tiene más de 90 días."""
        manager = SecretsManager()
        assert manager.check_rotation_needed() is True

    @patch.dict(
        "os.environ",
        {
            # Clave creada hace 45 días → no necesita rotación
            "JWT_SECRET_KEY_CREATED_AT": (
                datetime.now(UTC) - timedelta(days=45)
            ).isoformat(),
        },
        clear=True,
    )
    def test_returns_false_when_key_younger_than_90_days(self):
        """Retorna False si la clave activa tiene menos de 90 días."""
        manager = SecretsManager()
        assert manager.check_rotation_needed() is False

    def test_returns_false_at_89_days(self):
        """Con 89 días de antigüedad no se supera el umbral de 90 días."""
        # Usar 89 días para evitar condiciones de carrera con microsegundos
        eighty_nine_days_ago = datetime.now(UTC) - timedelta(days=89)

        with patch.dict(
            "os.environ",
            {"JWT_SECRET_KEY_CREATED_AT": eighty_nine_days_ago.isoformat()},
            clear=True,
        ):
            manager = SecretsManager()
            assert manager.check_rotation_needed() is False


class TestRotateJwtKey:
    """Tests para SecretsManager.rotate_jwt_key()."""

    @patch.dict(
        "os.environ",
        {"JWT_SECRET_KEY": "old_key_" + "x" * 56},
        clear=True,
    )
    @patch("app.configuracion.secrets_manager.SecretsManager._get_redis_client", return_value=None)
    @patch("app.configuracion.secrets_manager.SecretsManager._log_rotation_audit")
    def test_returns_new_64_char_hex_key(self, mock_audit, mock_redis):
        """rotate_jwt_key() debe retornar una clave hexadecimal de 64 caracteres."""
        manager = SecretsManager()
        nueva_clave = manager.rotate_jwt_key()

        assert len(nueva_clave) == 64
        assert all(c in "0123456789abcdef" for c in nueva_clave)

    @patch.dict(
        "os.environ",
        {"JWT_SECRET_KEY": "old_key_" + "x" * 56},
        clear=True,
    )
    @patch("app.configuracion.secrets_manager.SecretsManager._get_redis_client", return_value=None)
    @patch("app.configuracion.secrets_manager.SecretsManager._log_rotation_audit")
    def test_archives_current_key_as_previous(self, mock_audit, mock_redis):
        """La clave actual debe archivarse como JWT_SECRET_KEY_PREVIOUS."""
        clave_original = "old_key_" + "x" * 56
        manager = SecretsManager()
        manager.rotate_jwt_key()

        assert os.environ.get("JWT_SECRET_KEY_PREVIOUS") == clave_original

    @patch.dict(
        "os.environ",
        {"JWT_SECRET_KEY": "old_key_" + "x" * 56},
        clear=True,
    )
    @patch("app.configuracion.secrets_manager.SecretsManager._get_redis_client", return_value=None)
    @patch("app.configuracion.secrets_manager.SecretsManager._log_rotation_audit")
    def test_updates_active_key_in_env(self, mock_audit, mock_redis):
        """La nueva clave debe quedar en JWT_SECRET_KEY."""
        manager = SecretsManager()
        nueva_clave = manager.rotate_jwt_key()

        assert os.environ.get("JWT_SECRET_KEY") == nueva_clave

    @patch.dict(
        "os.environ",
        {"JWT_SECRET_KEY": "old_key_" + "x" * 56},
        clear=True,
    )
    @patch("app.configuracion.secrets_manager.SecretsManager._get_redis_client", return_value=None)
    @patch("app.configuracion.secrets_manager.SecretsManager._log_rotation_audit")
    def test_calls_audit_log(self, mock_audit, mock_redis):
        """rotate_jwt_key() debe registrar el evento en el audit log."""
        manager = SecretsManager()
        manager.rotate_jwt_key()

        mock_audit.assert_called_once()

    @patch.dict(
        "os.environ",
        {"JWT_SECRET_KEY": "old_key_" + "x" * 56},
        clear=True,
    )
    @patch("app.configuracion.secrets_manager.SecretsManager._log_rotation_audit")
    def test_raises_when_redis_lock_not_acquired(self, mock_audit):
        """Si el lock Redis no se puede adquirir, debe lanzar RuntimeError."""
        mock_redis = MagicMock()
        mock_redis.set.return_value = None  # Lock no adquirido (SET NX devuelve None)

        with patch(
            "app.configuracion.secrets_manager.SecretsManager._get_redis_client",
            return_value=mock_redis,
        ):
            manager = SecretsManager()
            with pytest.raises(RuntimeError, match="lock de rotación"):
                manager.rotate_jwt_key()

    @patch.dict(
        "os.environ",
        {"JWT_SECRET_KEY": "old_key_" + "x" * 56},
        clear=True,
    )
    @patch("app.configuracion.secrets_manager.SecretsManager._log_rotation_audit")
    def test_releases_redis_lock_after_rotation(self, mock_audit):
        """El lock Redis debe liberarse tras la rotación, incluso si hay error."""
        mock_redis = MagicMock()
        mock_redis.set.return_value = True  # Lock adquirido

        with patch(
            "app.configuracion.secrets_manager.SecretsManager._get_redis_client",
            return_value=mock_redis,
        ):
            manager = SecretsManager()
            manager.rotate_jwt_key()

        mock_redis.delete.assert_called_once_with("jwt_key_rotation_lock")

    @patch.dict(
        "os.environ",
        {"JWT_SECRET_KEY": "old_key_" + "x" * 56},
        clear=True,
    )
    @patch("app.configuracion.secrets_manager.SecretsManager._get_redis_client", return_value=None)
    @patch("app.configuracion.secrets_manager.SecretsManager._log_rotation_audit")
    def test_two_consecutive_rotations_produce_different_keys(self, mock_audit, mock_redis):
        """Dos rotaciones consecutivas deben producir claves distintas."""
        manager = SecretsManager()
        clave1 = manager.rotate_jwt_key()
        clave2 = manager.rotate_jwt_key()

        assert clave1 != clave2


class TestParseIsoDatetime:
    """Tests para el método estático _parse_iso_datetime."""

    def test_parses_valid_iso_string(self):
        """Debe parsear correctamente un string ISO 8601 con timezone."""
        raw = "2024-01-15T10:30:00+00:00"
        result = SecretsManager._parse_iso_datetime(raw)

        assert result is not None
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15

    def test_returns_none_for_empty_string(self):
        """Debe retornar None para string vacío."""
        assert SecretsManager._parse_iso_datetime("") is None

    def test_returns_none_for_none_input(self):
        """Debe retornar None para None."""
        assert SecretsManager._parse_iso_datetime(None) is None

    def test_returns_none_for_invalid_string(self):
        """Debe retornar None para string inválido sin lanzar excepción."""
        assert SecretsManager._parse_iso_datetime("not-a-date") is None

    def test_adds_utc_timezone_to_naive_datetime(self):
        """Debe agregar timezone UTC a datetimes sin timezone."""
        raw = "2024-06-01T12:00:00"
        result = SecretsManager._parse_iso_datetime(raw)

        assert result is not None
        assert result.tzinfo is not None
