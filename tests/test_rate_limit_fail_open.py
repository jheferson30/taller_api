"""
tests/test_rate_limit_fail_open.py — Tests de comportamiento fail-open cuando Redis no está disponible.

Verifica que:
- Cuando Redis falla al inicializar, _create_limiter() cae a memory://
- El log CRITICAL es emitido con los detalles del error
- Los requests siguen siendo permitidos (fail-open)

Valida: Requisito 1.6 (Fail-open cuando Redis no está disponible)
"""
import json
import logging
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address


class TestCreateLimiterFailOpen:
    """Tests para el comportamiento fail-open de _create_limiter()."""

    def test_falls_back_to_memory_when_redis_unavailable(self):
        """Cuando Redis no está disponible, debe crear el limiter con memory://."""
        import app.configuracion.limiter as limiter_module
        from slowapi import Limiter

        call_count = 0
        original_init = Limiter.__init__

        def mock_init_fail_first(self, *args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ConnectionError("Connection refused to redis:6379")
            return original_init(self, *args, **kwargs)

        with patch.object(Limiter, "__init__", mock_init_fail_first):
            with patch.object(limiter_module, "_log_redis_unavailable_fallback") as mock_log:
                result = limiter_module._create_limiter()

        # El limiter debe haberse creado (no None)
        assert result is not None
        # El log de fallback debe haberse llamado
        mock_log.assert_called_once()

    def test_log_redis_unavailable_fallback_called_with_exception(self):
        """_log_redis_unavailable_fallback debe recibir la excepción original."""
        from slowapi import Limiter

        original_error = ConnectionError("Redis connection refused")
        call_count = 0
        original_init = Limiter.__init__

        def mock_init_fail_first(self, *args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise original_error
            return original_init(self, *args, **kwargs)

        with patch.object(Limiter, "__init__", mock_init_fail_first):
            with patch("app.configuracion.limiter._log_redis_unavailable_fallback") as mock_log:
                from app.configuracion.limiter import _create_limiter
                _create_limiter()

        # Verificar que se llamó con la excepción y la URL
        mock_log.assert_called_once()
        call_args = mock_log.call_args
        assert call_args[0][0] is original_error  # primer argumento posicional es la excepción

    def test_critical_log_emitted_when_redis_unavailable(self):
        """El logger 'rate_limit' debe emitir un log CRITICAL cuando Redis falla."""
        from slowapi import Limiter

        call_count = 0
        original_init = Limiter.__init__

        def mock_init_fail_first(self, *args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ConnectionError("Redis unavailable")
            return original_init(self, *args, **kwargs)

        rate_limit_logger = logging.getLogger("rate_limit")

        with patch.object(Limiter, "__init__", mock_init_fail_first):
            with patch.object(rate_limit_logger, "critical") as mock_critical:
                from app.configuracion.limiter import _create_limiter
                _create_limiter()

        # Debe haberse emitido al menos un log CRITICAL
        assert mock_critical.called

    def test_critical_log_contains_required_fields(self):
        """El log CRITICAL debe contener event, severity, error y action."""
        from app.configuracion.limiter import _log_redis_unavailable_fallback

        rate_limit_logger = logging.getLogger("rate_limit")
        logged_messages = []

        def capture_critical(msg, *args, **kwargs):
            logged_messages.append(msg)

        with patch.object(rate_limit_logger, "critical", side_effect=capture_critical):
            error = ConnectionError("Redis connection refused")
            _log_redis_unavailable_fallback(error, "redis://redis:6379")

        assert len(logged_messages) == 1
        log_entry = json.loads(logged_messages[0])

        assert log_entry["event"] == "rate_limiter_redis_unavailable"
        assert log_entry["severity"] == "CRITICAL"
        assert "Redis connection refused" in log_entry["error"]
        assert log_entry["action"] == "fail_open"
        assert "timestamp" in log_entry

    def test_fallback_limiter_allows_requests(self):
        """Con el limiter en modo fallback (memory://), los requests deben ser permitidos."""
        # Crear un limiter con memory:// directamente (simula el fallback)
        fallback_limiter = Limiter(key_func=get_remote_address, storage_uri="memory://")

        app = FastAPI()
        app.state.limiter = fallback_limiter
        app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

        @app.get("/test")
        @fallback_limiter.limit("100/minute")
        def test_endpoint(request: Request):
            return {"ok": True, "storage": "memory"}

        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/test")
        assert response.status_code == 200
        assert response.json()["ok"] is True


class TestLogRedisUnavailable:
    """Tests para la función log_redis_unavailable del módulo rate_limit_logger."""

    def test_log_redis_unavailable_emits_critical(self):
        """log_redis_unavailable debe emitir un log CRITICAL al logger 'rate_limit'."""
        from app.utils.rate_limit_logger import log_redis_unavailable

        rate_limit_logger = logging.getLogger("rate_limit")
        logged_messages = []

        def capture_critical(msg, *args, **kwargs):
            logged_messages.append(msg)

        with patch.object(rate_limit_logger, "critical", side_effect=capture_critical):
            error = ConnectionError("Connection refused")
            log_redis_unavailable(error)

        assert len(logged_messages) == 1

    def test_log_redis_unavailable_json_structure(self):
        """El log debe ser JSON válido con los campos requeridos."""
        from app.utils.rate_limit_logger import log_redis_unavailable

        rate_limit_logger = logging.getLogger("rate_limit")
        logged_messages = []

        def capture_critical(msg, *args, **kwargs):
            logged_messages.append(msg)

        with patch.object(rate_limit_logger, "critical", side_effect=capture_critical):
            error = RuntimeError("Redis timeout after 5s")
            log_redis_unavailable(error)

        log_entry = json.loads(logged_messages[0])
        assert log_entry["event"] == "rate_limiter_redis_unavailable"
        assert log_entry["severity"] == "CRITICAL"
        assert "Redis timeout after 5s" in log_entry["error"]
        assert log_entry["action"] == "fail_open"
        assert "timestamp" in log_entry

    def test_log_redis_unavailable_includes_error_message(self):
        """El log debe incluir el mensaje de error de la excepción."""
        from app.utils.rate_limit_logger import log_redis_unavailable

        rate_limit_logger = logging.getLogger("rate_limit")
        logged_messages = []

        def capture_critical(msg, *args, **kwargs):
            logged_messages.append(msg)

        error_message = "ECONNREFUSED 127.0.0.1:6379"
        with patch.object(rate_limit_logger, "critical", side_effect=capture_critical):
            log_redis_unavailable(ConnectionRefusedError(error_message))

        log_entry = json.loads(logged_messages[0])
        assert error_message in log_entry["error"]
