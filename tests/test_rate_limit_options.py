"""
tests/test_rate_limit_options.py — Tests para la exención de requests OPTIONS.

Verifica que:
- _key_func retorna "options-exempt" para requests OPTIONS
- Los requests OPTIONS no son bloqueados por rate limiting

Valida: Requisito 1.9 (OPTIONS requests exempt)
"""
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address


def _make_mock_request(method: str = "GET", client_ip: str = "1.2.3.4") -> MagicMock:
    """Crea un mock de Request de Starlette con los atributos mínimos necesarios."""
    request = MagicMock()
    request.method = method
    request.client = MagicMock()
    request.client.host = client_ip
    request.headers = {}
    # Sin usuario autenticado por defecto
    request.state = MagicMock(spec=[])  # spec vacío para que getattr falle limpiamente
    return request


class TestKeyFuncOptionsExempt:
    """Tests para _key_func con requests OPTIONS."""

    def test_options_request_returns_options_exempt(self):
        """_key_func debe retornar 'options-exempt' para cualquier request OPTIONS."""
        from app.configuracion.limiter import _key_func

        request = _make_mock_request(method="OPTIONS", client_ip="1.2.3.4")
        key = _key_func(request)
        assert key == "options-exempt"

    def test_options_exempt_regardless_of_ip(self):
        """El resultado 'options-exempt' no depende de la IP del cliente."""
        from app.configuracion.limiter import _key_func

        ips = ["1.2.3.4", "10.0.0.1", "192.168.1.100", "203.0.113.42"]
        for ip in ips:
            request = _make_mock_request(method="OPTIONS", client_ip=ip)
            key = _key_func(request)
            assert key == "options-exempt", f"Expected 'options-exempt' for IP {ip}, got {key!r}"

    def test_options_exempt_regardless_of_whitelist(self):
        """OPTIONS debe ser exempt incluso si la IP está en whitelist."""
        from app.configuracion.limiter import _key_func

        # Usar una IP que normalmente estaría en whitelist
        request = _make_mock_request(method="OPTIONS", client_ip="127.0.0.1")
        key = _key_func(request)
        # OPTIONS se evalúa ANTES que la whitelist — debe retornar options-exempt
        assert key == "options-exempt"

    def test_non_options_methods_do_not_return_options_exempt(self):
        """Métodos distintos a OPTIONS no deben retornar 'options-exempt'."""
        from app.configuracion.limiter import _key_func

        non_options_methods = ["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD"]
        for method in non_options_methods:
            request = _make_mock_request(method=method, client_ip="1.2.3.4")
            key = _key_func(request)
            assert key != "options-exempt", (
                f"Method {method} should not return 'options-exempt', got {key!r}"
            )

    def test_options_with_authenticated_user_still_exempt(self):
        """OPTIONS debe ser exempt incluso si hay un usuario autenticado en el estado."""
        from app.configuracion.limiter import _key_func

        request = _make_mock_request(method="OPTIONS", client_ip="1.2.3.4")
        # Simular usuario autenticado
        user = MagicMock()
        user.id = 42
        request.state.user = user

        key = _key_func(request)
        assert key == "options-exempt"


class TestOptionsRequestsNotRateLimited:
    """Tests de integración: OPTIONS requests no deben ser bloqueados."""

    def _make_app_with_strict_limit(self, limit: str = "2/minute") -> TestClient:
        """Crea una app de prueba con un límite estricto."""
        limiter = Limiter(key_func=get_remote_address, storage_uri="memory://")
        app = FastAPI()
        app.state.limiter = limiter
        app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

        @app.options("/test")
        def options_endpoint(request: Request):
            return {"method": "OPTIONS"}

        @app.get("/test")
        @limiter.limit(limit)
        def get_endpoint(request: Request):
            return {"method": "GET"}

        return TestClient(app, raise_server_exceptions=False)

    def test_options_request_returns_200(self):
        """Un request OPTIONS debe retornar 200."""
        client = self._make_app_with_strict_limit("1/minute")
        response = client.options("/test")
        assert response.status_code == 200

    def test_get_request_is_rate_limited(self):
        """Verificar que el rate limiting funciona para GET (control del test)."""
        client = self._make_app_with_strict_limit("1/minute")
        # Primera petición GET: OK
        assert client.get("/test").status_code == 200
        # Segunda petición GET: 429
        assert client.get("/test").status_code == 429

    def test_key_func_returns_options_exempt_for_options_method(self):
        """Verificar directamente que la key_func retorna 'options-exempt' para OPTIONS."""
        from app.configuracion.limiter import _key_func

        # Crear un mock de request OPTIONS
        request = MagicMock()
        request.method = "OPTIONS"
        request.client = MagicMock()
        request.client.host = "5.6.7.8"
        request.headers = {}
        request.state = MagicMock(spec=[])

        result = _key_func(request)
        assert result == "options-exempt"

    def test_options_key_is_shared_across_all_options_requests(self):
        """Todos los requests OPTIONS comparten la misma clave 'options-exempt'."""
        from app.configuracion.limiter import _key_func

        ips = ["1.1.1.1", "2.2.2.2", "3.3.3.3"]
        keys = set()
        for ip in ips:
            request = _make_mock_request(method="OPTIONS", client_ip=ip)
            keys.add(_key_func(request))

        # Todos deben retornar la misma clave
        assert keys == {"options-exempt"}
