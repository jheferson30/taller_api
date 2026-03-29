"""
Tests para verificar que el rate limiting funciona correctamente.

Valida: Requirements 2.9, 3.9
"""
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded


def make_limited_app(limit_string: str = "2/minute") -> TestClient:
    """Crea una app de prueba con rate limiting configurado."""
    limiter = Limiter(key_func=get_remote_address, storage_uri="memory://")
    app = FastAPI()
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    @app.get("/test")
    @limiter.limit(limit_string)
    def test_endpoint(request: Request):
        return {"ok": True}

    return TestClient(app, raise_server_exceptions=False)


class TestRateLimitingWithinLimit:
    """Requests dentro del límite deben retornar respuestas normales (no 429)."""

    def test_single_request_returns_200(self):
        client = make_limited_app("2/minute")
        response = client.get("/test")
        assert response.status_code == 200
        assert response.json() == {"ok": True}

    def test_requests_within_limit_all_succeed(self):
        """Con límite de 2/minute, las primeras 2 peticiones deben ser exitosas."""
        client = make_limited_app("2/minute")
        for _ in range(2):
            response = client.get("/test")
            assert response.status_code == 200

    def test_higher_limit_allows_more_requests(self):
        """Con límite de 5/minute, las primeras 5 peticiones deben ser exitosas."""
        client = make_limited_app("5/minute")
        for _ in range(5):
            response = client.get("/test")
            assert response.status_code == 200


class TestRateLimitingExceedsLimit:
    """Requests que exceden el límite deben retornar 429."""

    def test_exceeding_limit_returns_429(self):
        """La petición que supera el límite debe retornar 429."""
        client = make_limited_app("2/minute")
        # Las primeras 2 deben pasar
        for _ in range(2):
            response = client.get("/test")
            assert response.status_code == 200
        # La tercera debe ser rechazada
        response = client.get("/test")
        assert response.status_code == 429

    def test_multiple_requests_after_limit_all_return_429(self):
        """Todas las peticiones después del límite deben retornar 429."""
        client = make_limited_app("1/minute")
        # Primera petición: OK
        response = client.get("/test")
        assert response.status_code == 200
        # Siguientes peticiones: 429
        for _ in range(3):
            response = client.get("/test")
            assert response.status_code == 429

    def test_limit_of_one_blocks_second_request(self):
        """Con límite de 1/minute, la segunda petición debe ser bloqueada."""
        client = make_limited_app("1/minute")
        assert client.get("/test").status_code == 200
        assert client.get("/test").status_code == 429

    def test_different_apps_have_independent_limits(self):
        """Cada instancia de app tiene su propio almacenamiento de límites."""
        client1 = make_limited_app("1/minute")
        client2 = make_limited_app("1/minute")

        # Agotar el límite en client1
        client1.get("/test")
        assert client1.get("/test").status_code == 429

        # client2 no debe verse afectado
        assert client2.get("/test").status_code == 200
