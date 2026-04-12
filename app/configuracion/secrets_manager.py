import os

from azure.core.exceptions import ResourceNotFoundError
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient


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
