"""
conftest.py — configuración global de pytest para el proyecto.

Establece las variables de entorno requeridas antes de que se importen
los módulos de la aplicación, de modo que las dependencias de seguridad
funcionen correctamente durante los tests.
"""
import os

from dotenv import load_dotenv
from hypothesis import HealthCheck, settings

# Cargar variables desde .env.test si existe (excluido de git)
load_dotenv(".env.test", override=False)

# ---------------------------------------------------------------------------
# Perfiles de Hypothesis
# ---------------------------------------------------------------------------
# ci: 100 ejemplos, suprime HealthCheck.too_slow para entornos de CI lentos
settings.register_profile("ci", max_examples=100, suppress_health_check=[HealthCheck.too_slow])
# dev: 50 ejemplos para ciclos de desarrollo más rápidos
settings.register_profile("dev", max_examples=50)
# Cargar perfil CI por defecto; se puede sobreescribir con HYPOTHESIS_PROFILE=dev
settings.load_profile(os.getenv("HYPOTHESIS_PROFILE", "ci"))

# Fallback vacío para entornos CI donde .env.test no existe —
# en CI las variables deben inyectarse como variables de entorno del sistema
os.environ.setdefault("PDF_PASSWORD", "")
os.environ.setdefault("ADMIN_PASSWORD", "")
os.environ.setdefault("JWT_SECRET_KEY", "test_secret_key_with_at_least_32_characters_for_security")
os.environ.setdefault("DATABASE_PASSWORD", "test_password")
os.environ.setdefault("CSRF_SECRET_KEY", "test_csrf_secret_key_with_at_least_32_characters_for_security")
os.environ.setdefault("PII_MASTER_KEY", "test_pii_master_key_with_at_least_64_characters_for_security_compliance")

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
