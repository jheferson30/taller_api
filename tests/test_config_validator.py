"""
Tests para el validador de configuración.
"""

import os
import pytest
from unittest.mock import patch

from app.configuracion.config_validator import (
    validate_config,
    ConfigValidationError,
    get_config_summary,
    _mask_sensitive,
)


class TestConfigValidator:
    """Tests para validate_config()."""
    
    def test_validate_config_with_valid_configuration(self):
        """Test que la validación pasa con configuración válida."""
        with patch.dict(os.environ, {
            "DATABASE_URL": "postgresql://user:pass@localhost/db",
            "JWT_SECRET_KEY": "a" * 32,  # 32 caracteres
            "ENVIRONMENT": "development",
            "BCRYPT_COST_FACTOR": "12",
            "JWT_ACCESS_TOKEN_EXPIRE_MINUTES": "15",
            "JWT_REFRESH_TOKEN_EXPIRE_DAYS": "7",
            "PASSWORD_MIN_LENGTH": "8",
        }):
            # No debe lanzar excepción
            validate_config()
    
    def test_validate_config_missing_database_url(self):
        """Test que falla si falta DATABASE_URL."""
        with patch.dict(os.environ, {
            "JWT_SECRET_KEY": "a" * 32,
        }, clear=True):
            with pytest.raises(ConfigValidationError):
                validate_config()
    
    def test_validate_config_missing_jwt_secret_key(self):
        """Test que falla si falta JWT_SECRET_KEY."""
        with patch.dict(os.environ, {
            "DATABASE_URL": "postgresql://user:pass@localhost/db",
        }, clear=True):
            with pytest.raises(ConfigValidationError):
                validate_config()
    
    def test_validate_config_jwt_secret_too_short(self):
        """Test que falla si JWT_SECRET_KEY es muy corto."""
        with patch.dict(os.environ, {
            "DATABASE_URL": "postgresql://user:pass@localhost/db",
            "JWT_SECRET_KEY": "short",  # Menos de 32 caracteres
        }):
            with pytest.raises(ConfigValidationError):
                validate_config()
    
    def test_validate_config_jwt_secret_default_value(self):
        """Test que falla si JWT_SECRET_KEY tiene valor por defecto."""
        with patch.dict(os.environ, {
            "DATABASE_URL": "postgresql://user:pass@localhost/db",
            "JWT_SECRET_KEY": "CAMBIAR_EN_PRODUCCION_usar_secreto_seguro",
        }):
            with pytest.raises(ConfigValidationError):
                validate_config()
    
    def test_validate_config_invalid_environment(self):
        """Test que falla si ENVIRONMENT es inválido."""
        with patch.dict(os.environ, {
            "DATABASE_URL": "postgresql://user:pass@localhost/db",
            "JWT_SECRET_KEY": "a" * 32,
            "ENVIRONMENT": "staging",  # No es válido
        }):
            with pytest.raises(ConfigValidationError):
                validate_config()
    
    def test_validate_config_invalid_bcrypt_cost_factor(self):
        """Test que falla si BCRYPT_COST_FACTOR es inválido."""
        with patch.dict(os.environ, {
            "DATABASE_URL": "postgresql://user:pass@localhost/db",
            "JWT_SECRET_KEY": "a" * 32,
            "BCRYPT_COST_FACTOR": "50",  # Fuera de rango
        }):
            with pytest.raises(ConfigValidationError):
                validate_config()
    
    def test_validate_config_invalid_access_token_expire(self):
        """Test que falla si JWT_ACCESS_TOKEN_EXPIRE_MINUTES es inválido."""
        with patch.dict(os.environ, {
            "DATABASE_URL": "postgresql://user:pass@localhost/db",
            "JWT_SECRET_KEY": "a" * 32,
            "JWT_ACCESS_TOKEN_EXPIRE_MINUTES": "-5",  # Negativo
        }):
            with pytest.raises(ConfigValidationError):
                validate_config()
    
    def test_validate_config_invalid_refresh_token_expire(self):
        """Test que falla si JWT_REFRESH_TOKEN_EXPIRE_DAYS es inválido."""
        with patch.dict(os.environ, {
            "DATABASE_URL": "postgresql://user:pass@localhost/db",
            "JWT_SECRET_KEY": "a" * 32,
            "JWT_REFRESH_TOKEN_EXPIRE_DAYS": "0",  # Cero
        }):
            with pytest.raises(ConfigValidationError):
                validate_config()
    
    def test_validate_config_invalid_password_min_length(self):
        """Test que falla si PASSWORD_MIN_LENGTH es muy corto."""
        with patch.dict(os.environ, {
            "DATABASE_URL": "postgresql://user:pass@localhost/db",
            "JWT_SECRET_KEY": "a" * 32,
            "PASSWORD_MIN_LENGTH": "3",  # Menos de 6
        }):
            with pytest.raises(ConfigValidationError):
                validate_config()


class TestGetConfigSummary:
    """Tests para get_config_summary()."""
    
    def test_get_config_summary_returns_list(self):
        """Test que retorna una lista de tuplas."""
        with patch.dict(os.environ, {
            "DATABASE_URL": "postgresql://user:pass@localhost/db",
            "JWT_SECRET_KEY": "a" * 32,
        }):
            summary = get_config_summary()
            
            assert isinstance(summary, list)
            assert len(summary) > 0
            assert all(isinstance(item, tuple) and len(item) == 2 for item in summary)
    
    def test_get_config_summary_masks_sensitive_values(self):
        """Test que enmascara valores sensibles."""
        with patch.dict(os.environ, {
            "DATABASE_URL": "postgresql://user:pass@localhost/db",
            "JWT_SECRET_KEY": "supersecretkey123456789012345678",
        }):
            summary = get_config_summary()
            summary_dict = dict(summary)
            
            # Verificar que valores sensibles están enmascarados
            assert "..." in summary_dict["DATABASE_URL"]
            assert "..." in summary_dict["JWT_SECRET_KEY"]
            
            # Verificar que no se muestra el valor completo
            assert "supersecretkey123456789012345678" not in summary_dict["JWT_SECRET_KEY"]


class TestMaskSensitive:
    """Tests para _mask_sensitive()."""
    
    def test_mask_sensitive_short_value(self):
        """Test que enmascara valores cortos completamente."""
        assert _mask_sensitive("short") == "***"
        assert _mask_sensitive("1234567") == "***"
    
    def test_mask_sensitive_long_value(self):
        """Test que enmascara valores largos mostrando inicio y fin."""
        result = _mask_sensitive("supersecretkey123456")
        
        assert result.startswith("supe")
        assert result.endswith("3456")
        assert "..." in result
        assert "secretkey" not in result
    
    def test_mask_sensitive_empty_value(self):
        """Test que maneja valores vacíos."""
        assert _mask_sensitive("") == "***"
        assert _mask_sensitive(None) == "***"
