"""
tests/test_rate_limit_unauthenticated.py — Tests para rate limiting de requests no autenticados.

Verifica que:
- Requests sin JWT usan solo el contador de IP (clave = IP, no "user:...")
- Requests con JWT válido usan la clave "user:{user_id}"
- Casos límite: user=None, user.id=None → clave IP

Valida: Requisito 3.7 (Unauthenticated requests use IP-only limiting)
"""
from unittest.mock import MagicMock, patch

import pytest


def _make_mock_request(
    method: str = "GET",
    client_ip: str = "1.2.3.4",
    user=None,
    has_user_attr: bool = False,
) -> MagicMock:
    """
    Crea un mock de Request de Starlette.

    Args:
        method: Método HTTP del request.
        client_ip: IP del cliente.
        user: Objeto usuario para request.state.user (None = no autenticado).
        has_user_attr: Si True, establece request.state.user = user.
                       Si False, request.state no tiene atributo 'user'.
    """
    request = MagicMock()
    request.method = method
    request.client = MagicMock()
    request.client.host = client_ip
    request.headers = {}

    if has_user_attr:
        # Simular que el middleware de auth estableció request.state.user
        state = MagicMock()
        state.user = user
        request.state = state
    else:
        # Sin atributo user en state (request no autenticado)
        request.state = MagicMock(spec=[])  # spec vacío: getattr lanza AttributeError

    return request


class TestKeyFuncUnauthenticated:
    """Tests para _key_func con requests sin autenticación."""

    def test_unauthenticated_request_returns_ip_key(self):
        """Sin JWT, la clave debe ser la IP del cliente."""
        from app.configuracion.limiter import _key_func

        client_ip = "203.0.113.42"
        request = _make_mock_request(client_ip=client_ip, has_user_attr=False)

        key = _key_func(request)

        assert key == client_ip
        assert not key.startswith("user:")

    def test_unauthenticated_request_key_is_not_user_prefixed(self):
        """La clave para requests no autenticados nunca debe tener prefijo 'user:'."""
        from app.configuracion.limiter import _key_func

        ips = ["1.2.3.4", "10.0.0.1", "192.168.1.100", "172.16.0.1"]
        for ip in ips:
            request = _make_mock_request(client_ip=ip, has_user_attr=False)
            key = _key_func(request)
            assert not key.startswith("user:"), (
                f"IP {ip}: expected IP key, got {key!r}"
            )

    def test_user_none_returns_ip_key(self):
        """Cuando request.state.user es None, debe usar la IP como clave."""
        from app.configuracion.limiter import _key_func

        client_ip = "5.6.7.8"
        request = _make_mock_request(client_ip=client_ip, user=None, has_user_attr=True)

        key = _key_func(request)

        assert key == client_ip
        assert not key.startswith("user:")

    def test_user_with_none_id_returns_ip_key(self):
        """Cuando user.id es None, debe usar la IP como clave (no 'user:None')."""
        from app.configuracion.limiter import _key_func

        client_ip = "9.10.11.12"
        user = MagicMock()
        user.id = None
        request = _make_mock_request(client_ip=client_ip, user=user, has_user_attr=True)

        key = _key_func(request)

        assert key == client_ip
        assert key != "user:None"
        assert not key.startswith("user:")

    def test_different_unauthenticated_ips_get_different_keys(self):
        """Cada IP no autenticada debe tener su propia clave independiente."""
        from app.configuracion.limiter import _key_func

        ip1 = "1.1.1.1"
        ip2 = "2.2.2.2"

        request1 = _make_mock_request(client_ip=ip1, has_user_attr=False)
        request2 = _make_mock_request(client_ip=ip2, has_user_attr=False)

        key1 = _key_func(request1)
        key2 = _key_func(request2)

        assert key1 == ip1
        assert key2 == ip2
        assert key1 != key2


class TestKeyFuncAuthenticated:
    """Tests para _key_func con requests autenticados (JWT presente)."""

    def test_authenticated_request_returns_user_key(self):
        """Con JWT válido, la clave debe ser 'user:{user_id}'."""
        from app.configuracion.limiter import _key_func

        user_id = 42
        user = MagicMock()
        user.id = user_id
        request = _make_mock_request(client_ip="1.2.3.4", user=user, has_user_attr=True)

        key = _key_func(request)

        assert key == f"user:{user_id}"

    def test_user_key_format_is_user_colon_id(self):
        """La clave de usuario debe tener el formato exacto 'user:{id}'."""
        from app.configuracion.limiter import _key_func

        test_ids = [1, 100, 9999, 10000]
        for user_id in test_ids:
            user = MagicMock()
            user.id = user_id
            request = _make_mock_request(client_ip="1.2.3.4", user=user, has_user_attr=True)
            key = _key_func(request)
            assert key == f"user:{user_id}", f"Expected 'user:{user_id}', got {key!r}"

    def test_same_user_different_ips_get_same_key(self):
        """El mismo usuario desde distintas IPs debe tener la misma clave."""
        from app.configuracion.limiter import _key_func

        user_id = 77
        ips = ["1.1.1.1", "2.2.2.2", "3.3.3.3"]
        keys = set()

        for ip in ips:
            user = MagicMock()
            user.id = user_id
            request = _make_mock_request(client_ip=ip, user=user, has_user_attr=True)
            keys.add(_key_func(request))

        # Todos deben retornar la misma clave de usuario
        assert keys == {f"user:{user_id}"}

    def test_different_users_same_ip_get_different_keys(self):
        """Usuarios distintos desde la misma IP deben tener claves distintas."""
        from app.configuracion.limiter import _key_func

        ip = "1.2.3.4"
        user_ids = [1, 2, 3]
        keys = []

        for user_id in user_ids:
            user = MagicMock()
            user.id = user_id
            request = _make_mock_request(client_ip=ip, user=user, has_user_attr=True)
            keys.append(_key_func(request))

        # Todas las claves deben ser distintas
        assert len(set(keys)) == len(user_ids)
        for i, user_id in enumerate(user_ids):
            assert keys[i] == f"user:{user_id}"

    def test_authenticated_key_does_not_include_ip(self):
        """La clave de usuario autenticado no debe incluir la IP."""
        from app.configuracion.limiter import _key_func

        client_ip = "203.0.113.42"
        user = MagicMock()
        user.id = 99
        request = _make_mock_request(client_ip=client_ip, user=user, has_user_attr=True)

        key = _key_func(request)

        assert client_ip not in key
        assert key == "user:99"


class TestKeyFuncBoundaryCases:
    """Tests de casos límite para _key_func."""

    def test_user_object_without_id_attribute_falls_back_to_ip(self):
        """Si el objeto user no tiene atributo 'id', debe usar la IP."""
        from app.configuracion.limiter import _key_func

        client_ip = "7.8.9.10"
        # Crear un objeto user sin atributo 'id'
        user = MagicMock(spec=[])  # spec vacío: no tiene ningún atributo
        request = _make_mock_request(client_ip=client_ip, user=user, has_user_attr=True)

        key = _key_func(request)

        assert key == client_ip
        assert not key.startswith("user:")

    def test_whitelist_ip_returns_whitelist_exempt(self):
        """Una IP en whitelist debe retornar 'whitelist-exempt' (no la IP)."""
        from app.configuracion.limiter import _key_func

        # 127.0.0.1 siempre está en whitelist
        request = _make_mock_request(method="GET", client_ip="127.0.0.1", has_user_attr=False)

        key = _key_func(request)

        assert key == "whitelist-exempt"

    def test_whitelist_ip_with_user_still_returns_whitelist_exempt(self):
        """Una IP en whitelist con usuario autenticado debe retornar 'whitelist-exempt'."""
        from app.configuracion.limiter import _key_func

        user = MagicMock()
        user.id = 42
        # 127.0.0.1 siempre está en whitelist
        request = _make_mock_request(
            method="GET", client_ip="127.0.0.1", user=user, has_user_attr=True
        )

        key = _key_func(request)

        # La whitelist se evalúa antes que el usuario
        assert key == "whitelist-exempt"

    def test_non_whitelist_ip_without_user_returns_ip(self):
        """Una IP que no está en whitelist y sin usuario debe retornar la IP."""
        from app.configuracion.limiter import _key_func

        # IP que definitivamente no está en whitelist
        client_ip = "203.0.113.1"
        request = _make_mock_request(method="GET", client_ip=client_ip, has_user_attr=False)

        with patch("app.configuracion.limiter._get_whitelist_ips", return_value=frozenset({"127.0.0.1", "::1"})):
            key = _key_func(request)

        assert key == client_ip
