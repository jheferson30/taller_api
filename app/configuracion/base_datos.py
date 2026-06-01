import os
from urllib.parse import quote_plus

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker


def _get_database_url() -> str:
    """
    Construye la URL de la base de datos, recuperando la contraseña desde SecretsManager.

    Si AZURE_KEY_VAULT_URL está configurado, intenta recuperar la contraseña desde Key Vault.
    Si no, usa la contraseña de la variable de entorno DATABASE_PASSWORD o la URL completa.

    Returns:
        URL de conexión a la base de datos
    """
    # Si DATABASE_URL está completamente configurada, usarla directamente
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        return database_url

    # Construir URL desde componentes individuales
    db_host = os.getenv("DATABASE_HOST", "localhost")
    db_port = os.getenv("DATABASE_PORT", "5432")
    db_name = os.getenv("DATABASE_NAME", "taller_db")
    db_user = os.getenv("DATABASE_USER", "postgres")

    # Intentar recuperar contraseña desde SecretsManager
    db_password = None
    try:
        from app.configuracion.secrets_manager import SecretsManager

        secrets_manager = SecretsManager()
        db_password = secrets_manager.get_secret(
            "database-password", fallback_env_var="DATABASE_PASSWORD"
        )
    except Exception:
        # Si falla SecretsManager, intentar variable de entorno directamente
        db_password = os.getenv("DATABASE_PASSWORD")
        if not db_password:
            raise RuntimeError(
                "Secreto requerido no configurado: 'DATABASE_PASSWORD'. "
                "Configurar en Azure Key Vault como 'database-password' "
                "o como variable de entorno 'DATABASE_PASSWORD'."
            )

    # URL encode la contraseña para manejar caracteres especiales
    db_password_encoded = quote_plus(db_password)

    return f"postgresql+psycopg2://{db_user}:{db_password_encoded}@{db_host}:{db_port}/{db_name}?client_encoding=utf8"


DATABASE_URL = _get_database_url()

engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def obtener_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
