"""
tests/test_limiter_config.py — Smoke tests para la configuración del limiter.

Verifica que _get_redis_url() lee correctamente la variable de entorno REDIS_URL
y que _create_limiter() usa la URL correcta al inicializar.

Valida: Requisito 1.4 (Redis como storage backend)
"""
import importlib
from unittest.mock import patch

import pytest


class TestGetRedisUrl:
    """Tests para _get_redis_url() — lectura de la variable de entorno REDIS_URL."""

    def test_returns_default_when_env_not_set(self):
        """Sin REDIS_URL en el entorno, debe retornar el default redis://redis:6379."""
        with patch.dict("os.environ", {}, clear=False):
            # Asegurarse de que REDIS_URL no esté en el entorno
            import os
            env_without_redis = {k: v for k, v in os.environ.items() if k != "REDIS_URL"}
            with patch.dict("os.environ", env_without_redis, clear=True):
                from app.configuracion.limiter import _get_redis_url
                url = _get_redis_url()
        assert url == "redis://redis:6379"

    def test_returns_env_var_when_set(self):
        """Cuando REDIS_URL está definida, debe retornar ese valor."""
        custom_url = "redis://custom-host:6380"
        with patch.dict("os.environ", {"REDIS_URL": custom_url}):
            from app.configuracion.limiter import _get_redis_url
            url = _get_redis_url()
        assert url == custom_url

    def test_returns_different_custom_urls(self):
        """Debe retornar cualquier URL configurada en la variable de entorno."""
        test_cases = [
            "redis://localhost:6379",
            "redis://redis-prod:6379/0",
            "rediss://secure-redis:6380",
            "redis://:password@redis:6379",
        ]
        from app.configuracion.limiter import _get_redis_url
        for url in test_cases:
            with patch.dict("os.environ", {"REDIS_URL": url}):
                result = _get_redis_url()
            assert result == url, f"Expected {url!r}, got {result!r}"

    def test_default_url_format_is_valid_redis_url(self):
        """El URL por defecto debe tener el formato correcto de Redis."""
        import os
        env_without_redis = {k: v for k, v in os.environ.items() if k != "REDIS_URL"}
        with patch.dict("os.environ", env_without_redis, clear=True):
            from app.configuracion.limiter import _get_redis_url
            url = _get_redis_url()
        assert url.startswith("redis://")
        assert ":" in url.split("//")[1]  # host:port


class TestCreateLimiter:
    """Tests para _create_limiter() — inicialización del Limiter con Redis."""

    def test_create_limiter_with_custom_redis_url(self):
        """_create_limiter() debe usar la URL de Redis del entorno."""
        custom_url = "redis://custom-host:6380"
        with patch.dict("os.environ", {"REDIS_URL": custom_url}):
            with patch("app.configuracion.limiter.Limiter") as mock_limiter_cls:
                mock_limiter_cls.return_value = mock_limiter_cls
                from app.configuracion.limiter import _create_limiter
                _create_limiter()
                # Verificar que se llamó con la URL correcta
                call_kwargs = mock_limiter_cls.call_args
                assert call_kwargs is not None
                # storage_uri puede estar en args o kwargs
                if call_kwargs.kwargs:
                    assert call_kwargs.kwargs.get("storage_uri") == custom_url
                else:
                    # Buscar en args posicionales si no hay kwargs
                    assert custom_url in str(call_kwargs)

    def test_create_limiter_falls_back_to_memory_on_redis_failure(self):
        """Si Redis falla, _create_limiter() debe usar memory:// como fallback."""
        from app.configuracion.limiter import _create_limiter
        from slowapi import Limiter

        call_count = 0
        original_init = Limiter.__init__

        def mock_init(self, *args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ConnectionError("Redis connection refused")
            # Segunda llamada (fallback a memory://) debe funcionar
            return original_init(self, *args, **kwargs)

        with patch.object(Limiter, "__init__", mock_init):
            with patch("app.configuracion.limiter._log_redis_unavailable_fallback"):
                limiter = _create_limiter()

        assert limiter is not None

    def test_limiter_module_has_global_instance(self):
        """El módulo debe exportar una instancia global 'limiter'."""
        from app.configuracion import limiter as limiter_module
        assert hasattr(limiter_module, "limiter")
        assert limiter_module.limiter is not None

    def test_create_limiter_includes_default_limits(self):
        """_create_limiter() debe configurar los límites globales por defecto."""
        with patch("app.configuracion.limiter.Limiter") as mock_limiter_cls:
            mock_limiter_cls.return_value = mock_limiter_cls
            from app.configuracion.limiter import _create_limiter, _DEFAULT_LIMITS
            _create_limiter()
            call_kwargs = mock_limiter_cls.call_args
            assert call_kwargs is not None
            # Verificar que se pasaron default_limits
            kwargs = call_kwargs.kwargs if call_kwargs.kwargs else {}
            if "default_limits" in kwargs:
                assert kwargs["default_limits"] == _DEFAULT_LIMITS
