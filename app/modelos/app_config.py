from dataclasses import dataclass


@dataclass
class AppConfig:
    """Application configuration loaded from environment and secrets."""

    # Database
    database_url: str

    # JWT
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 15
    jwt_refresh_token_expire_days: int = 7

    # Secrets Manager
    azure_key_vault_url: str | None = None
    use_key_vault: bool = False

    # Celery
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/0"

    # File Upload
    max_file_size: int = 10 * 1024 * 1024  # 10 MB
    allowed_mime_types: list = None

    # Environment
    environment: str = "development"

    def __post_init__(self):
        if self.allowed_mime_types is None:
            self.allowed_mime_types = ["image/jpeg", "image/png", "image/webp", "application/pdf"]
