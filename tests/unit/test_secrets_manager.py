"""
Unit tests for SecretsManager class.

Tests cover:
- Key Vault retrieval with mocked Azure SDK
- Fallback to environment variables
- Error handling for missing secrets
"""
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
