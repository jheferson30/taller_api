"""
conftest.py — configuración global de pytest para el proyecto.

Establece las variables de entorno requeridas antes de que se importen
los módulos de la aplicación, de modo que las dependencias de seguridad
funcionen correctamente durante los tests.
"""
import os
from dotenv import load_dotenv

# Cargar variables desde .env.test si existe (excluido de git)
load_dotenv(".env.test", override=False)

# Fallback vacío para entornos CI donde .env.test no existe —
# en CI las variables deben inyectarse como variables de entorno del sistema
os.environ.setdefault("PDF_PASSWORD", "")
os.environ.setdefault("ADMIN_PASSWORD", "")
os.environ.setdefault("JWT_SECRET_KEY", "test_secret_key_with_at_least_32_characters_for_security")

# Rate limiting configuration for tests (higher limits to avoid test failures)
os.environ.setdefault("RATE_LIMIT_AUTH_PER_MINUTE", "1000")
os.environ.setdefault("RATE_LIMIT_REFRESH_PER_MINUTE", "1000")
os.environ.setdefault("RATE_LIMIT_FORGOT_PASSWORD_PER_HOUR", "1000")
os.environ.setdefault("RATE_LIMIT_CREATE_PER_MINUTE", "1000")
os.environ.setdefault("RATE_LIMIT_READ_PER_MINUTE", "1000")

def pytest_configure(config):
    """
    Registra markers personalizados para pytest.
    """
    config.addinivalue_line(
        "markers", "property_test: marca tests basados en propiedades (property-based tests)"
    )
