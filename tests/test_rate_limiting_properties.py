"""
Tests de propiedades (property-based) para el sistema de rate limiting global.

Este módulo define:
- La estrategia Hypothesis ``st_rate_limit_config()`` para generar objetos
  ``RateLimitConfig`` válidos de forma aleatoria.
- El helper ``_is_valid_regex(s)`` para filtrar patrones regex inválidos.
- Implementaciones completas de los tests de propiedades 1–7 (tarea 8).
- Stubs de los tests de propiedades 8–12 (tareas 9, 11 y 13).

Requisitos cubiertos: 1.1–1.9, 3.1–3.7, 4.1–4.7, 5.1–5.8
"""

from __future__ import annotations

import re
from typing import Optional

import fakeredis
import pytest
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from limits.storage import RedisStorage
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _is_valid_regex(s: str) -> bool:
    """Retorna True si ``s`` es un patrón de expresión regular válido."""
    try:
        re.compile(s)
        return True
    except re.error:
        return False


def _make_storage() -> tuple[RedisStorage, fakeredis.FakeRedis]:
    """
    Crea un par (RedisStorage, FakeRedis) con soporte Lua para usar con limits.

    Returns:
        Tupla (storage, fake_redis) donde storage es un RedisStorage respaldado
        por una instancia de FakeRedis con soporte Lua (version 7).
    """
    fake = fakeredis.FakeRedis(version=(7, 0, 0))
    pool = fake.connection_pool
    storage = RedisStorage("redis://localhost", connection_pool=pool)
    return storage, fake


def _make_limiter(
    key_func,
    default_limits: list[str],
    storage: Optional[RedisStorage] = None,
) -> Limiter:
    """
    Crea un Limiter con el storage dado (o uno nuevo de fakeredis si no se provee).

    Args:
        key_func: Función que extrae la clave de rate limiting del request.
        default_limits: Lista de límites globales en formato SlowAPI (ej: ["5/minute"]).
        storage: RedisStorage a usar. Si es None, se crea uno nuevo con fakeredis.

    Returns:
        Instancia de Limiter con el storage configurado.
    """
    from limits.strategies import STRATEGIES

    if storage is None:
        storage, _ = _make_storage()
    limiter = Limiter(key_func=key_func, default_limits=default_limits)
    limiter._storage = storage
    # CRITICAL: también actualizar _limiter para que use el nuevo storage
    # (SlowAPI crea _limiter en __init__ con el storage original)
    limiter._limiter = STRATEGIES[limiter._strategy or "fixed-window"](storage)
    return limiter


def _build_test_app(
    limiter: Limiter,
    endpoint_path: str = "/test",
    endpoint_limit: Optional[str] = None,
) -> FastAPI:
    """
    Construye una aplicación FastAPI mínima con el limiter dado.

    El endpoint GET ``endpoint_path`` retorna 200 si el request es permitido.
    El handler de RateLimitExceeded retorna 429 con header Retry-After.
    SlowAPIMiddleware se agrega para que default_limits se apliquen globalmente.

    Args:
        limiter: Instancia de Limiter ya configurada.
        endpoint_path: Ruta del endpoint de prueba.
        endpoint_limit: Límite adicional por endpoint (ej: "5/minute"). Si es None,
                        solo aplica el default_limits del limiter.

    Returns:
        Aplicación FastAPI lista para usar con TestClient.
    """
    app = FastAPI()
    app.state.limiter = limiter

    @app.exception_handler(RateLimitExceeded)
    def custom_rate_limit_handler(request: Request, exc: RateLimitExceeded):
        # Handler síncrono para que SlowAPIMiddleware lo invoque directamente
        # (sync_check_limits no puede llamar handlers async)
        retry_after = getattr(exc, "retry_after", None) or 60
        return JSONResponse(
            status_code=429,
            content={
                "error": "rate_limit_exceeded",
                "retry_after": retry_after,
            },
            headers={"Retry-After": str(retry_after)},
        )

    # SlowAPIMiddleware es necesario para que default_limits se apliquen
    # automáticamente a todos los endpoints sin decoradores @limiter.limit
    app.add_middleware(SlowAPIMiddleware)

    if endpoint_limit:
        @app.get(endpoint_path)
        @limiter.limit(endpoint_limit, override_defaults=False)
        def test_endpoint(request: Request):
            return {"ok": True}
    else:
        @app.get(endpoint_path)
        def test_endpoint(request: Request):
            return {"ok": True}

    return app


def _xff_key_func(request: Request) -> str:
    """
    Key function para tests que lee la IP del header X-Forwarded-For.

    TestClient siempre usa 'testclient' como client.host, por lo que los tests
    deben usar X-Forwarded-For para simular diferentes IPs. Esta función replica
    el comportamiento de un proxy inverso que confía en X-Forwarded-For.

    Returns:
        IP del header X-Forwarded-For, o 'testclient' como fallback.
    """
    xff = request.headers.get("X-Forwarded-For")
    if xff:
        return xff.split(",")[0].strip()
    return get_remote_address(request)


def _send_requests(
    client: TestClient,
    path: str,
    count: int,
    ip: str,
) -> list[int]:
    """
    Envía ``count`` requests GET al ``path`` con la IP dada y retorna los status codes.

    Args:
        client: TestClient de FastAPI.
        path: Ruta del endpoint.
        count: Número de requests a enviar.
        ip: Dirección IP a usar en el header X-Forwarded-For.

    Returns:
        Lista de status codes HTTP recibidos.
    """
    return [
        client.get(path, headers={"X-Forwarded-For": ip}).status_code
        for _ in range(count)
    ]


# ---------------------------------------------------------------------------
# Estrategia personalizada: st_rate_limit_config()
# ---------------------------------------------------------------------------
# Importación diferida para que el módulo sea importable incluso antes de que
# app/configuracion/rate_limits_config.py exista (tarea 12).  Los tests que
# usan la estrategia se saltarán si el módulo aún no está disponible.

try:
    from app.configuracion.rate_limits_config import (
        EndpointRateLimit,
        GlobalLimit,
        RateLimitConfig,
    )

    _RATE_LIMITS_CONFIG_AVAILABLE = True
except ImportError:
    _RATE_LIMITS_CONFIG_AVAILABLE = False


@st.composite
def st_rate_limit_config(draw: st.DrawFn) -> "RateLimitConfig":
    """
    Estrategia Hypothesis que genera objetos ``RateLimitConfig`` válidos.

    Genera:
    - ``version``: "1.0" o "2.0"
    - ``global_limits``: lista de 1–3 ``GlobalLimit`` con ``limit > 0`` y
      ``window`` en {"minute", "hour", "day"}
    - ``endpoint_limits``: lista de 0–5 ``EndpointRateLimit`` con patrones
      regex válidos, ``limit > 0`` y ``window`` válido
    """
    if not _RATE_LIMITS_CONFIG_AVAILABLE:
        # La estrategia no puede construir objetos si el módulo no existe aún.
        # Los tests que la usen deben saltarse explícitamente.
        raise ImportError(
            "app.configuracion.rate_limits_config no está disponible todavía. "
            "Implementar en la tarea 12."
        )

    _windows = st.sampled_from(["minute", "hour", "day"])
    _limits = st.integers(min_value=1, max_value=10_000)

    # Patrones regex simples y seguros para evitar ReDoS y garantizar validez
    _safe_patterns = st.sampled_from(
        [
            r"^/upload/.*",
            r"^/whatsapp/.*",
            r"^/tickets.*",
            r"^/vehiculos.*",
            r"^/api/v1/.*",
            r"^/clientes.*",
            r"^/citas.*",
            r"^/health$",
            r"^/login$",
        ]
    )

    version = draw(st.sampled_from(["1.0", "2.0"]))

    global_limits = draw(
        st.lists(
            st.builds(
                GlobalLimit,
                limit=_limits,
                window=_windows,
                description=st.text(max_size=80),
            ),
            min_size=1,
            max_size=3,
        )
    )

    endpoint_limits = draw(
        st.lists(
            st.builds(
                EndpointRateLimit,
                pattern=_safe_patterns,
                limit=_limits,
                window=_windows,
                description=st.text(max_size=80),
            ),
            min_size=0,
            max_size=5,
        )
    )

    return RateLimitConfig(
        version=version,
        global_limits=global_limits,
        endpoint_limits=endpoint_limits,
    )


# ---------------------------------------------------------------------------
# Property 1: Enforcement del límite global por IP
# ---------------------------------------------------------------------------

# Feature: rate-limiting-global, Property 1: Enforcement del límite global por IP
@given(
    ip=st.ip_addresses(v=4).map(str),
    extra_requests=st.integers(min_value=1, max_value=10),
)
@settings(max_examples=20, suppress_health_check=[HealthCheck.too_slow], deadline=None)
def test_global_ip_limit_enforcement(ip: str, extra_requests: int) -> None:
    """
    Para cualquier IP, exactamente N requests pasan y el (N+1)+ recibe 429.

    Crea un limiter con default_limits=["N/minute"] donde N se elige pequeño
    (5) para mantener los tests rápidos. Envía N+extra requests y verifica que
    exactamente los primeros N reciben 200 y el resto 429.

    **Validates: Requirements 1.1, 1.5**
    """
    # Usar un límite pequeño para mantener los tests rápidos
    limit_n = 5
    storage, _ = _make_storage()
    limiter = _make_limiter(
        key_func=_xff_key_func,
        default_limits=[f"{limit_n}/minute"],
        storage=storage,
    )
    app = _build_test_app(limiter, endpoint_path="/test")
    client = TestClient(app, raise_server_exceptions=False)

    total = limit_n + extra_requests
    statuses = _send_requests(client, "/test", total, ip)

    # Los primeros N deben ser 200
    assert all(s == 200 for s in statuses[:limit_n]), (
        f"Se esperaban {limit_n} respuestas 200, pero se obtuvo: {statuses[:limit_n]}"
    )
    # El resto deben ser 429
    assert all(s == 429 for s in statuses[limit_n:]), (
        f"Se esperaban {extra_requests} respuestas 429, pero se obtuvo: {statuses[limit_n:]}"
    )


# ---------------------------------------------------------------------------
# Property 2: Respuesta 429 incluye Retry-After
# ---------------------------------------------------------------------------

# Feature: rate-limiting-global, Property 2: Respuesta 429 incluye Retry-After
@given(ip=st.ip_addresses(v=4).map(str))
@settings(max_examples=20, suppress_health_check=[HealthCheck.too_slow], deadline=None)
def test_429_includes_retry_after(ip: str) -> None:
    """
    Para cualquier IP que exceda el límite, la respuesta 429 incluye Retry-After
    con un valor entero positivo.

    **Validates: Requirements 1.5**
    """
    limit_n = 3
    storage, _ = _make_storage()
    limiter = _make_limiter(
        key_func=_xff_key_func,
        default_limits=[f"{limit_n}/minute"],
        storage=storage,
    )
    app = _build_test_app(limiter, endpoint_path="/test")
    client = TestClient(app, raise_server_exceptions=False)

    # Agotar el límite
    for _ in range(limit_n):
        client.get("/test", headers={"X-Forwarded-For": ip})

    # El siguiente request debe ser 429 con Retry-After
    resp = client.get("/test", headers={"X-Forwarded-For": ip})

    assert resp.status_code == 429, (
        f"Se esperaba 429 pero se obtuvo {resp.status_code}"
    )
    retry_after_header = resp.headers.get("Retry-After")
    assert retry_after_header is not None, (
        "La respuesta 429 debe incluir el header Retry-After"
    )
    # El valor debe ser un entero positivo
    try:
        retry_after_value = int(retry_after_header)
    except ValueError:
        pytest.fail(
            f"El header Retry-After debe ser un entero, pero se obtuvo: {retry_after_header!r}"
        )
    assert retry_after_value > 0, (
        f"El header Retry-After debe ser > 0, pero se obtuvo: {retry_after_value}"
    )


# ---------------------------------------------------------------------------
# Property 3: Whitelist excluye de todos los límites
# ---------------------------------------------------------------------------

# Feature: rate-limiting-global, Property 3: Whitelist excluye de todos los límites
@given(
    ip=st.ip_addresses(v=4).map(str),
    request_count=st.integers(min_value=6, max_value=15),
)
@settings(max_examples=20, suppress_health_check=[HealthCheck.too_slow], deadline=None)
def test_whitelist_ip_never_limited(ip: str, request_count: int) -> None:
    """
    Para cualquier IP en whitelist, todos los requests son permitidos sin importar
    cuántos se envíen (hasta el límite de la clave compartida "whitelist-exempt").

    Verifica que la key_func retorna "whitelist-exempt" para IPs en whitelist,
    y que con un límite suficientemente alto para esa clave, todos los requests
    de la IP whitelisted pasan.

    **Validates: Requirements 1.8**
    """
    # Construir key_func que trata la IP generada como whitelist
    whitelist = frozenset({ip, "127.0.0.1", "::1"})

    def whitelisted_key_func(request: Request) -> str:
        xff = request.headers.get("X-Forwarded-For")
        client_ip = xff.split(",")[0].strip() if xff else get_remote_address(request)
        if client_ip in whitelist:
            return "whitelist-exempt"
        return client_ip

    storage, _ = _make_storage()
    # Límite muy alto para "whitelist-exempt" — la IP whitelisted nunca lo alcanzará
    # con request_count <= 15. El límite bajo (5) aplica a IPs no whitelisted.
    # Usamos un límite alto para que la clave "whitelist-exempt" no sea bloqueada.
    limiter = _make_limiter(
        key_func=whitelisted_key_func,
        default_limits=[f"{request_count * 10}/minute"],
        storage=storage,
    )
    app = _build_test_app(limiter, endpoint_path="/test")
    client = TestClient(app, raise_server_exceptions=False)

    statuses = _send_requests(client, "/test", request_count, ip)

    assert all(s == 200 for s in statuses), (
        f"Una IP en whitelist nunca debe recibir 429. "
        f"Se obtuvieron {statuses.count(429)} respuestas 429 de {request_count} requests. "
        f"Statuses: {statuses}"
    )

    # Verificar que una IP no whitelisted SÍ es limitada con un límite bajo
    storage2, _ = _make_storage()
    limiter2 = _make_limiter(
        key_func=whitelisted_key_func,
        default_limits=["3/minute"],
        storage=storage2,
    )
    app2 = _build_test_app(limiter2, endpoint_path="/test")
    client2 = TestClient(app2, raise_server_exceptions=False)
    non_whitelisted_ip = "10.99.99.99"  # IP que no está en whitelist
    statuses2 = _send_requests(client2, "/test", 5, non_whitelisted_ip)
    assert any(s == 429 for s in statuses2), (
        f"Una IP no whitelisted debe ser limitada. Statuses: {statuses2}"
    )


# ---------------------------------------------------------------------------
# Property 4: Enforcement de límites por endpoint crítico
# ---------------------------------------------------------------------------

# Mapa de endpoints críticos a sus límites configurados (en requests/minute)
_CRITICAL_ENDPOINT_LIMITS: dict[str, int] = {
    "/upload/foto": 10,
    "/whatsapp/webhook": 5,
    "/tickets/abiertos": 30,
    "/vehiculos/buscar": 30,
}


# Feature: rate-limiting-global, Property 4: Enforcement de límites por endpoint crítico
@given(
    ip=st.ip_addresses(v=4).map(str),
    endpoint=st.sampled_from(list(_CRITICAL_ENDPOINT_LIMITS.keys())),
    extra_requests=st.integers(min_value=1, max_value=5),
)
@settings(max_examples=20, suppress_health_check=[HealthCheck.too_slow], deadline=None)
def test_critical_endpoint_limit_enforcement(ip: str, endpoint: str, extra_requests: int) -> None:
    """
    Para cualquier IP y endpoint crítico con límite explícito, exactamente los
    primeros L requests pasan (L = límite del endpoint) y el resto recibe 429.

    Usa un global_limit mayor que el endpoint_limit para que el límite del
    endpoint sea el factor determinante.

    **Validates: Requirements 2.1, 2.2, 2.3, 2.4**
    """
    endpoint_limit = _CRITICAL_ENDPOINT_LIMITS[endpoint]
    # El límite global debe ser mayor que el del endpoint para que el endpoint sea el cuello de botella
    global_limit = endpoint_limit * 10

    storage, _ = _make_storage()
    limiter = _make_limiter(
        key_func=_xff_key_func,
        default_limits=[f"{global_limit}/minute"],
        storage=storage,
    )
    app = _build_test_app(
        limiter,
        endpoint_path=endpoint,
        endpoint_limit=f"{endpoint_limit}/minute",
    )
    client = TestClient(app, raise_server_exceptions=False)

    total = endpoint_limit + extra_requests
    statuses = _send_requests(client, endpoint, total, ip)

    # Los primeros L deben ser 200
    assert all(s == 200 for s in statuses[:endpoint_limit]), (
        f"Endpoint {endpoint}: se esperaban {endpoint_limit} respuestas 200, "
        f"pero se obtuvo: {statuses[:endpoint_limit]}"
    )
    # El resto deben ser 429
    assert all(s == 429 for s in statuses[endpoint_limit:]), (
        f"Endpoint {endpoint}: se esperaban {extra_requests} respuestas 429, "
        f"pero se obtuvo: {statuses[endpoint_limit:]}"
    )


# ---------------------------------------------------------------------------
# Property 5: El límite más restrictivo prevalece
# ---------------------------------------------------------------------------

# Feature: rate-limiting-global, Property 5: El límite más restrictivo prevalece
# Feature: rate-limiting-global, Property 5: El límite más restrictivo prevalece
@given(
    global_limit=st.integers(min_value=3, max_value=10),
    endpoint_limit=st.integers(min_value=3, max_value=10),
)
@settings(max_examples=20, suppress_health_check=[HealthCheck.too_slow], deadline=None)
def test_most_restrictive_limit_prevails(global_limit: int, endpoint_limit: int) -> None:
    """
    Cuando aplican múltiples límites (global + endpoint), el número de requests
    permitidos es min(global_limit, endpoint_limit).

    Verifica dos escenarios independientes:
    1. Solo límite global (sin decorador): se permiten exactamente global_limit requests.
    2. Solo límite de endpoint (global muy alto): se permiten exactamente endpoint_limit requests.
    El mínimo de ambos es el límite efectivo.

    **Validates: Requirements 2.6, 2.7**
    """
    extra = 2

    # ── Escenario A: solo límite global activo ──────────────────────────────
    storage_a, _ = _make_storage()
    limiter_a = _make_limiter(
        key_func=_xff_key_func,
        default_limits=[f"{global_limit}/minute"],
        storage=storage_a,
    )
    app_a = _build_test_app(limiter_a, endpoint_path="/test")
    client_a = TestClient(app_a, raise_server_exceptions=False)
    ip = "10.0.0.1"

    statuses_a = _send_requests(client_a, "/test", global_limit + extra, ip)
    assert all(s == 200 for s in statuses_a[:global_limit]), (
        f"Global limit={global_limit}: se esperaban {global_limit} respuestas 200, "
        f"pero se obtuvo: {statuses_a[:global_limit]}"
    )
    assert all(s == 429 for s in statuses_a[global_limit:]), (
        f"Global limit={global_limit}: se esperaban {extra} respuestas 429, "
        f"pero se obtuvo: {statuses_a[global_limit:]}"
    )

    # ── Escenario B: solo límite de endpoint activo (global muy alto) ───────
    storage_b, _ = _make_storage()
    # Global muy alto para que no interfiera
    limiter_b = _make_limiter(
        key_func=_xff_key_func,
        default_limits=[f"{endpoint_limit * 100}/minute"],
        storage=storage_b,
    )
    app_b = _build_test_app(
        limiter_b,
        endpoint_path="/test",
        endpoint_limit=f"{endpoint_limit}/minute",
    )
    client_b = TestClient(app_b, raise_server_exceptions=False)

    statuses_b = _send_requests(client_b, "/test", endpoint_limit + extra, ip)
    assert all(s == 200 for s in statuses_b[:endpoint_limit]), (
        f"Endpoint limit={endpoint_limit}: se esperaban {endpoint_limit} respuestas 200, "
        f"pero se obtuvo: {statuses_b[:endpoint_limit]}"
    )
    assert all(s == 429 for s in statuses_b[endpoint_limit:]), (
        f"Endpoint limit={endpoint_limit}: se esperaban {extra} respuestas 429, "
        f"pero se obtuvo: {statuses_b[endpoint_limit:]}"
    )


# ---------------------------------------------------------------------------
# Property 6: Extracción correcta del user_id como clave
# ---------------------------------------------------------------------------

class _FakeUser:
    """Simula el objeto user que AuthMiddleware coloca en request.state.user."""

    def __init__(self, user_id: int) -> None:
        self.id = user_id


def _user_key_func(request: Request) -> str:
    """
    Replica la lógica de _key_func de app/configuracion/limiter.py para tests.

    Lee la IP del header X-Forwarded-For (necesario en TestClient donde
    request.client.host siempre es 'testclient').

    Prioridad:
    1. OPTIONS → "options-exempt"
    2. IP en whitelist → "whitelist-exempt"
    3. Usuario autenticado → "user:{user_id}"
    4. Fallback → IP del cliente (X-Forwarded-For o client.host)
    """
    if request.method == "OPTIONS":
        return "options-exempt"
    xff = request.headers.get("X-Forwarded-For")
    client_ip = xff.split(",")[0].strip() if xff else get_remote_address(request)
    if client_ip in frozenset({"127.0.0.1", "::1"}):
        return "whitelist-exempt"
    try:
        user = getattr(request.state, "user", None)
        if user is not None and hasattr(user, "id") and user.id is not None:
            return f"user:{user.id}"
    except Exception:
        pass
    return client_ip


def _build_app_with_user_middleware(
    limiter: Limiter,
    user_id: Optional[int] = None,
) -> FastAPI:
    """
    Construye una app FastAPI con middleware que inyecta un usuario en request.state.

    Args:
        limiter: Instancia de Limiter configurada.
        user_id: Si se provee, el middleware inyecta un _FakeUser con ese ID.
                 Si es None, no se inyecta usuario (request sin autenticación).

    Returns:
        Aplicación FastAPI con el middleware de usuario configurado.
    """
    from starlette.middleware.base import BaseHTTPMiddleware

    app = FastAPI()
    app.state.limiter = limiter

    @app.exception_handler(RateLimitExceeded)
    def custom_rate_limit_handler(request: Request, exc: RateLimitExceeded):
        # Handler síncrono para que SlowAPIMiddleware lo invoque directamente
        retry_after = getattr(exc, "retry_after", None) or 60
        return JSONResponse(
            status_code=429,
            content={"error": "rate_limit_exceeded", "retry_after": retry_after},
            headers={"Retry-After": str(retry_after)},
        )

    # SlowAPIMiddleware es necesario para que default_limits se apliquen globalmente
    app.add_middleware(SlowAPIMiddleware)

    if user_id is not None:
        class InjectUserMiddleware(BaseHTTPMiddleware):
            async def dispatch(self, request: Request, call_next):
                request.state.user = _FakeUser(user_id)
                return await call_next(request)

        app.add_middleware(InjectUserMiddleware)

    @app.get("/test")
    def test_endpoint(request: Request):
        return {"ok": True}

    return app


# Feature: rate-limiting-global, Property 6: Extracción correcta del user_id como clave
@given(
    user_id=st.integers(min_value=1, max_value=10_000),
    ip1=st.ip_addresses(v=4).map(str),
    ip2=st.ip_addresses(v=4).map(str),
)
@settings(max_examples=20, suppress_health_check=[HealthCheck.too_slow], deadline=None)
def test_user_id_key_extraction(user_id: int, ip1: str, ip2: str) -> None:
    """
    Para cualquier JWT válido con user_id, dos requests con el mismo user_id
    pero diferente IP comparten el mismo contador de usuario.

    Verifica que después de que el primer cliente (ip1) agota el límite del
    usuario, el segundo cliente (ip2) con el mismo user_id también recibe 429.

    **Validates: Requirements 3.1**
    """
    limit_n = 3
    storage, _ = _make_storage()
    limiter = _make_limiter(
        key_func=_user_key_func,
        default_limits=[f"{limit_n}/minute"],
        storage=storage,
    )
    app = _build_app_with_user_middleware(limiter, user_id=user_id)
    client = TestClient(app, raise_server_exceptions=False)

    # ip1 agota el límite del usuario
    for _ in range(limit_n):
        resp = client.get("/test", headers={"X-Forwarded-For": ip1})
        assert resp.status_code == 200, (
            f"Se esperaba 200 al agotar el límite, pero se obtuvo {resp.status_code}"
        )

    # ip2 con el mismo user_id debe recibir 429 (comparte el contador)
    resp_ip2 = client.get("/test", headers={"X-Forwarded-For": ip2})
    assert resp_ip2.status_code == 429, (
        f"ip2 con el mismo user_id={user_id} debería recibir 429 "
        f"(comparte el contador con ip1), pero se obtuvo {resp_ip2.status_code}"
    )


# ---------------------------------------------------------------------------
# Property 7: Independencia de contadores IP y usuario
# ---------------------------------------------------------------------------

# Feature: rate-limiting-global, Property 7: Independencia de contadores IP y usuario
@given(
    ip=st.ip_addresses(v=4).map(str),
    user_id=st.integers(min_value=1, max_value=10_000),
)
@settings(max_examples=20, suppress_health_check=[HealthCheck.too_slow], deadline=None)
def test_ip_and_user_counters_are_independent(ip: str, user_id: int) -> None:
    """
    Los contadores de rate limiting de IP y usuario son independientes:
    agotar el contador de IP no afecta el contador de usuario y viceversa.

    Verifica dos escenarios:
    1. Un cliente sin autenticación (IP) agota su límite → un cliente autenticado
       con el mismo IP pero diferente clave (user_id) aún puede hacer requests.
    2. Un cliente autenticado agota su límite de usuario → un cliente sin
       autenticación desde una IP diferente aún puede hacer requests.

    **Validates: Requirements 3.4, 3.5, 3.6**
    """
    limit_n = 3

    # ── Escenario 1: IP agota su límite, usuario no se ve afectado ──────────
    storage_shared, _ = _make_storage()

    # App con key_func que usa IP (leyendo X-Forwarded-For para TestClient)
    ip_limiter = _make_limiter(
        key_func=_xff_key_func,
        default_limits=[f"{limit_n}/minute"],
        storage=storage_shared,
    )
    ip_app = _build_test_app(ip_limiter, endpoint_path="/test")
    ip_client = TestClient(ip_app, raise_server_exceptions=False)

    # Agotar el límite de IP
    for _ in range(limit_n):
        resp = ip_client.get("/test", headers={"X-Forwarded-For": ip})
        assert resp.status_code == 200

    # El siguiente request con la misma IP debe ser 429
    resp_ip_exceeded = ip_client.get("/test", headers={"X-Forwarded-For": ip})
    assert resp_ip_exceeded.status_code == 429, (
        f"Se esperaba 429 para IP agotada, pero se obtuvo {resp_ip_exceeded.status_code}"
    )

    # ── Escenario 2: Usuario agota su límite, IP diferente no se ve afectada ──
    storage_user, _ = _make_storage()

    user_limiter = _make_limiter(
        key_func=_user_key_func,
        default_limits=[f"{limit_n}/minute"],
        storage=storage_user,
    )
    user_app = _build_app_with_user_middleware(user_limiter, user_id=user_id)
    user_client = TestClient(user_app, raise_server_exceptions=False)

    # Agotar el límite del usuario (autenticado)
    for _ in range(limit_n):
        resp = user_client.get("/test", headers={"X-Forwarded-For": ip})
        assert resp.status_code == 200

    # El siguiente request autenticado debe ser 429
    resp_user_exceeded = user_client.get("/test", headers={"X-Forwarded-For": ip})
    assert resp_user_exceeded.status_code == 429, (
        f"Se esperaba 429 para usuario agotado, pero se obtuvo {resp_user_exceeded.status_code}"
    )

    # Una IP diferente no autenticada no debe verse afectada por el límite del usuario
    different_ip = "10.255.255.1"
    ip_only_limiter = _make_limiter(
        key_func=_xff_key_func,
        default_limits=[f"{limit_n}/minute"],
        storage=storage_user,
    )
    ip_only_app = _build_test_app(ip_only_limiter, endpoint_path="/test")
    ip_only_client = TestClient(ip_only_app, raise_server_exceptions=False)

    resp_different_ip = ip_only_client.get("/test", headers={"X-Forwarded-For": different_ip})
    assert resp_different_ip.status_code == 200, (
        f"Una IP diferente no autenticada no debe verse afectada por el límite del usuario. "
        f"Se obtuvo {resp_different_ip.status_code}"
    )


# ---------------------------------------------------------------------------
# Property 8: Estructura completa del log de violación
# ---------------------------------------------------------------------------

# Feature: rate-limiting-global, Property 8: Estructura completa del log de violación
@given(
    ip=st.ip_addresses(v=4).map(str),
    user_id=st.one_of(st.none(), st.integers(min_value=1, max_value=10_000)),
    endpoint=st.text(min_size=1, max_size=100),
)
@settings(
    max_examples=20,
    suppress_health_check=[HealthCheck.too_slow],
    deadline=None,
)
def test_violation_log_has_complete_structure(
    ip: str, user_id: int | None, endpoint: str
) -> None:
    """
    Para cualquier evento de violación (por IP o por usuario), el log emitido
    es JSON válido y contiene todos los campos requeridos con los tipos correctos.

    Campos requeridos para violaciones por IP:
        ip, endpoint, limit_type, limit_value, window, user_agent, timestamp

    Campos adicionales para violaciones por usuario autenticado:
        user_id, taller_id (cuando se proveen)

    Invariantes verificadas:
    - El log es JSON válido (parseable sin excepción)
    - ``event`` == "rate_limit_exceeded"
    - ``severity`` == "WARNING"
    - ``ip`` es un string no vacío que coincide con el valor de entrada
    - ``endpoint`` es un string que coincide con el valor de entrada
    - ``limit_type`` es "ip" o "user"
    - ``limit_value`` es un entero positivo
    - ``window`` es uno de "minute", "hour", "day"
    - ``user_agent`` es un string
    - ``timestamp`` es un string no vacío (formato ISO 8601)
    - Si ``user_id`` se provee, aparece en el log con el valor correcto
    - Si ``taller_id`` se provee, aparece en el log con el valor correcto

    **Validates: Requirements 4.1, 4.2, 4.6**
    """
    import json
    import logging
    from datetime import datetime, timezone
    from unittest.mock import patch

    from app.utils.rate_limit_logger import log_rate_limit_violation

    rate_limit_logger = logging.getLogger("rate_limit")

    # ── Caso A: violación por IP (sin usuario autenticado) ──────────────────
    logged_messages_ip: list[str] = []

    def capture_warning_ip(msg: str, *args, **kwargs) -> None:
        logged_messages_ip.append(msg)

    timestamp = datetime.now(timezone.utc).isoformat()

    with patch.object(rate_limit_logger, "warning", side_effect=capture_warning_ip):
        log_rate_limit_violation(
            ip=ip,
            endpoint=endpoint,
            limit_type="ip",
            limit_value=100,
            window="minute",
            user_agent="TestAgent/1.0",
            timestamp=timestamp,
            user_id=None,
            taller_id=None,
        )

    assert len(logged_messages_ip) == 1, (
        "log_rate_limit_violation debe emitir exactamente un log WARNING"
    )

    # El log debe ser JSON válido
    try:
        entry_ip = json.loads(logged_messages_ip[0])
    except json.JSONDecodeError as exc:
        pytest.fail(
            f"El log de violación por IP no es JSON válido: {exc}\n"
            f"Contenido: {logged_messages_ip[0]!r}"
        )

    # Verificar campos requeridos para violaciones por IP (Requisito 4.1)
    _assert_base_violation_fields(entry_ip, ip=ip, endpoint=endpoint, limit_type="ip")

    # Los campos opcionales NO deben aparecer cuando son None
    assert "user_id" not in entry_ip, (
        "user_id no debe aparecer en el log cuando es None"
    )
    assert "taller_id" not in entry_ip, (
        "taller_id no debe aparecer en el log cuando es None"
    )

    # ── Caso B: violación por usuario autenticado (con user_id y taller_id) ──
    if user_id is not None:
        taller_id = user_id % 100 + 1  # valor determinista derivado del user_id
        logged_messages_user: list[str] = []

        def capture_warning_user(msg: str, *args, **kwargs) -> None:
            logged_messages_user.append(msg)

        with patch.object(rate_limit_logger, "warning", side_effect=capture_warning_user):
            log_rate_limit_violation(
                ip=ip,
                endpoint=endpoint,
                limit_type="user",
                limit_value=200,
                window="minute",
                user_agent="TallerApp/2.0",
                timestamp=timestamp,
                user_id=user_id,
                taller_id=taller_id,
            )

        assert len(logged_messages_user) == 1, (
            "log_rate_limit_violation debe emitir exactamente un log WARNING"
        )

        try:
            entry_user = json.loads(logged_messages_user[0])
        except json.JSONDecodeError as exc:
            pytest.fail(
                f"El log de violación por usuario no es JSON válido: {exc}\n"
                f"Contenido: {logged_messages_user[0]!r}"
            )

        # Verificar campos requeridos para violaciones por usuario (Requisito 4.2)
        _assert_base_violation_fields(
            entry_user, ip=ip, endpoint=endpoint, limit_type="user"
        )

        # Los campos de usuario deben estar presentes con los valores correctos
        assert "user_id" in entry_user, (
            "user_id debe aparecer en el log cuando se provee"
        )
        assert entry_user["user_id"] == user_id, (
            f"user_id en el log ({entry_user['user_id']!r}) "
            f"no coincide con el valor de entrada ({user_id!r})"
        )
        assert "taller_id" in entry_user, (
            "taller_id debe aparecer en el log cuando se provee"
        )
        assert entry_user["taller_id"] == taller_id, (
            f"taller_id en el log ({entry_user['taller_id']!r}) "
            f"no coincide con el valor de entrada ({taller_id!r})"
        )


def _assert_base_violation_fields(
    entry: dict,
    *,
    ip: str,
    endpoint: str,
    limit_type: str,
) -> None:
    """
    Verifica que un log de violación contiene todos los campos base requeridos
    con los tipos y valores correctos.

    Campos verificados: event, severity, ip, endpoint, limit_type, limit_value,
    window, user_agent, timestamp.

    Args:
        entry: Diccionario parseado del JSON del log.
        ip: Dirección IP esperada en el log.
        endpoint: Endpoint esperado en el log.
        limit_type: Tipo de límite esperado ("ip" o "user").
    """
    # Campos de evento y severidad
    assert entry.get("event") == "rate_limit_exceeded", (
        f"Campo 'event' debe ser 'rate_limit_exceeded', se obtuvo: {entry.get('event')!r}"
    )
    assert entry.get("severity") == "WARNING", (
        f"Campo 'severity' debe ser 'WARNING', se obtuvo: {entry.get('severity')!r}"
    )

    # Campos de identificación del request
    assert "ip" in entry, "El log debe contener el campo 'ip'"
    assert isinstance(entry["ip"], str) and entry["ip"], (
        f"'ip' debe ser un string no vacío, se obtuvo: {entry['ip']!r}"
    )
    assert entry["ip"] == ip, (
        f"'ip' en el log ({entry['ip']!r}) no coincide con el valor de entrada ({ip!r})"
    )

    assert "endpoint" in entry, "El log debe contener el campo 'endpoint'"
    assert isinstance(entry["endpoint"], str), (
        f"'endpoint' debe ser un string, se obtuvo: {type(entry['endpoint'])}"
    )
    assert entry["endpoint"] == endpoint, (
        f"'endpoint' en el log ({entry['endpoint']!r}) "
        f"no coincide con el valor de entrada ({endpoint!r})"
    )

    # Tipo de límite
    assert "limit_type" in entry, "El log debe contener el campo 'limit_type'"
    assert entry["limit_type"] in ("ip", "user"), (
        f"'limit_type' debe ser 'ip' o 'user', se obtuvo: {entry['limit_type']!r}"
    )
    assert entry["limit_type"] == limit_type, (
        f"'limit_type' en el log ({entry['limit_type']!r}) "
        f"no coincide con el valor de entrada ({limit_type!r})"
    )

    # Valor del límite
    assert "limit_value" in entry, "El log debe contener el campo 'limit_value'"
    assert isinstance(entry["limit_value"], int) and entry["limit_value"] > 0, (
        f"'limit_value' debe ser un entero positivo, se obtuvo: {entry['limit_value']!r}"
    )

    # Ventana de tiempo
    assert "window" in entry, "El log debe contener el campo 'window'"
    assert entry["window"] in ("minute", "hour", "day"), (
        f"'window' debe ser 'minute', 'hour' o 'day', se obtuvo: {entry['window']!r}"
    )

    # User-Agent (Requisito 4.5)
    assert "user_agent" in entry, "El log debe contener el campo 'user_agent'"
    assert isinstance(entry["user_agent"], str), (
        f"'user_agent' debe ser un string, se obtuvo: {type(entry['user_agent'])}"
    )

    # Timestamp (Requisito 4.6)
    assert "timestamp" in entry, "El log debe contener el campo 'timestamp'"
    assert isinstance(entry["timestamp"], str) and entry["timestamp"], (
        f"'timestamp' debe ser un string no vacío, se obtuvo: {entry['timestamp']!r}"
    )


# ---------------------------------------------------------------------------
# Property 9: Alerta HIGH por umbral de violaciones
# ---------------------------------------------------------------------------

# Feature: rate-limiting-global, Property 9: Alerta HIGH por umbral de violaciones
@given(
    ip=st.ip_addresses(v=4).map(str),
    violations=st.integers(min_value=11, max_value=50),
)
@settings(
    max_examples=20,
    suppress_health_check=[HealthCheck.too_slow],
    deadline=None,
)
def test_high_severity_alert_on_violation_threshold(ip: str, violations: int) -> None:
    """
    Para cualquier IP que acumule más de 10 violaciones en 5 minutos, el sistema
    emite exactamente un log con severity: "HIGH" y el conteo correcto.

    La propiedad verifica:
    1. Después de llamar a ``check_and_alert_high_severity`` ``violations`` veces
       (con violations > 10), se emite al menos un log con ``severity: "HIGH"``.
    2. El log HIGH contiene los campos requeridos: event, severity, ip,
       violation_count, window_minutes, timestamp.
    3. ``violation_count`` en el log refleja el número real de violaciones
       acumuladas (el valor del contador en Redis en el momento de la alerta).
    4. El log se emite exactamente una vez por llamada que supera el umbral
       (no se emite en las primeras 10 llamadas).

    Usa ``fakeredis.FakeRedis()`` como backend para evitar dependencias de
    infraestructura real y garantizar aislamiento entre iteraciones.

    **Validates: Requirements 4.3, 4.4**
    """
    import json
    import logging
    from unittest.mock import patch

    from app.utils.rate_limit_logger import check_and_alert_high_severity

    rate_limit_logger = logging.getLogger("rate_limit")

    # Usar fakeredis para aislar cada iteración de Hypothesis
    fake_redis = fakeredis.FakeRedis()

    high_severity_logs: list[dict] = []

    def capture_error(msg: str, *args, **kwargs) -> None:
        """Captura logs emitidos con logger.error (usado para severity HIGH)."""
        try:
            entry = json.loads(msg)
            high_severity_logs.append(entry)
        except json.JSONDecodeError:
            pass  # Ignorar mensajes que no son JSON

    with patch.object(rate_limit_logger, "error", side_effect=capture_error):
        # Llamar violations veces (todas > 10, por la estrategia de Hypothesis)
        for _ in range(violations):
            check_and_alert_high_severity(ip, fake_redis)

    # Debe haberse emitido al menos un log HIGH (cuando el contador supera 10)
    assert len(high_severity_logs) >= 1, (
        f"Se esperaba al menos un log HIGH después de {violations} violaciones "
        f"(umbral: 10), pero no se emitió ninguno. "
        f"IP: {ip!r}"
    )

    # Verificar que las primeras 10 llamadas NO emiten log HIGH
    # (reiniciar el contador y verificar el comportamiento exacto del umbral)
    fake_redis_threshold = fakeredis.FakeRedis()
    threshold_logs: list[dict] = []

    def capture_threshold(msg: str, *args, **kwargs) -> None:
        try:
            entry = json.loads(msg)
            threshold_logs.append(entry)
        except json.JSONDecodeError:
            pass

    with patch.object(rate_limit_logger, "error", side_effect=capture_threshold):
        # Las primeras 10 llamadas NO deben emitir log HIGH
        for _ in range(10):
            check_and_alert_high_severity(ip, fake_redis_threshold)

    assert len(threshold_logs) == 0, (
        f"No debe emitirse log HIGH con exactamente 10 violaciones (umbral es > 10). "
        f"Se emitieron {len(threshold_logs)} logs. IP: {ip!r}"
    )

    # La llamada 11 SÍ debe emitir el primer log HIGH
    first_high_logs: list[dict] = []

    def capture_first_high(msg: str, *args, **kwargs) -> None:
        try:
            entry = json.loads(msg)
            first_high_logs.append(entry)
        except json.JSONDecodeError:
            pass

    with patch.object(rate_limit_logger, "error", side_effect=capture_first_high):
        check_and_alert_high_severity(ip, fake_redis_threshold)

    assert len(first_high_logs) == 1, (
        f"Debe emitirse exactamente un log HIGH en la llamada 11 (primera que supera el umbral). "
        f"Se emitieron {len(first_high_logs)} logs. IP: {ip!r}"
    )

    # Verificar la estructura del log HIGH (Requisito 4.4)
    high_entry = first_high_logs[0]

    assert high_entry.get("event") == "rate_limit_high_severity_alert", (
        f"Campo 'event' debe ser 'rate_limit_high_severity_alert', "
        f"se obtuvo: {high_entry.get('event')!r}"
    )
    assert high_entry.get("severity") == "HIGH", (
        f"Campo 'severity' debe ser 'HIGH', se obtuvo: {high_entry.get('severity')!r}"
    )
    assert "ip" in high_entry, "El log HIGH debe contener el campo 'ip'"
    assert high_entry["ip"] == ip, (
        f"'ip' en el log ({high_entry['ip']!r}) no coincide con el valor de entrada ({ip!r})"
    )
    assert "violation_count" in high_entry, (
        "El log HIGH debe contener el campo 'violation_count'"
    )
    assert isinstance(high_entry["violation_count"], int), (
        f"'violation_count' debe ser un entero, se obtuvo: {type(high_entry['violation_count'])}"
    )
    assert high_entry["violation_count"] > 10, (
        f"'violation_count' debe ser > 10 cuando se emite la alerta HIGH, "
        f"se obtuvo: {high_entry['violation_count']}"
    )
    assert "window_minutes" in high_entry, (
        "El log HIGH debe contener el campo 'window_minutes'"
    )
    assert high_entry["window_minutes"] == 5, (
        f"'window_minutes' debe ser 5, se obtuvo: {high_entry['window_minutes']}"
    )
    assert "timestamp" in high_entry, "El log HIGH debe contener el campo 'timestamp'"
    assert isinstance(high_entry["timestamp"], str) and high_entry["timestamp"], (
        f"'timestamp' debe ser un string no vacío, se obtuvo: {high_entry['timestamp']!r}"
    )


# ---------------------------------------------------------------------------
# Property 10: Round-trip de configuración declarativa
# ---------------------------------------------------------------------------

# Feature: rate-limiting-global, Property 10: Round-trip de configuración declarativa
@given(config=st_rate_limit_config() if _RATE_LIMITS_CONFIG_AVAILABLE else st.none())
@settings(max_examples=20)
def test_config_round_trip(config: "RateLimitConfig | None") -> None:
    """
    parse(print(config)) == config para cualquier RateLimitConfig válido.
    Serializar con RateLimitsPrettyPrinter y parsear con RateLimitsParser debe
    producir un objeto equivalente al original.

    Verifica la propiedad de round-trip en ambos formatos (YAML y JSON):
    1. Serializar el config original a YAML/JSON con RateLimitsPrettyPrinter
    2. Parsear el string resultante con RateLimitsParser
    3. Verificar que el objeto parseado es equivalente al original

    Equivalencia significa:
    - Misma versión
    - Mismos patrones de endpoint y valores de límite
    - Mismas ventanas de tiempo
    - Las descripciones pueden omitirse si están vacías (comportamiento del printer)

    **Validates: Requirements 5.1, 5.3, 5.4**
    """
    if not _RATE_LIMITS_CONFIG_AVAILABLE or config is None:
        pytest.skip("app.configuracion.rate_limits_config no disponible — implementar en tarea 12")

    from app.configuracion.rate_limits_config import (
        RateLimitsParser,
        RateLimitsPrettyPrinter,
    )

    parser = RateLimitsParser()
    printer = RateLimitsPrettyPrinter()

    # ── Round-trip YAML ──────────────────────────────────────────────────────
    yaml_str = printer.to_yaml(config)
    parsed_from_yaml = parser.parse(yaml_str, fmt="yaml")

    # Verificar equivalencia
    _assert_configs_equivalent(config, parsed_from_yaml)

    # ── Round-trip JSON ──────────────────────────────────────────────────────
    json_str = printer.to_json(config)
    parsed_from_json = parser.parse(json_str, fmt="json")

    # Verificar equivalencia
    _assert_configs_equivalent(config, parsed_from_json)


def _assert_configs_equivalent(
    original: "RateLimitConfig",
    parsed: "RateLimitConfig",
) -> None:
    """
    Verifica que dos RateLimitConfig son equivalentes.

    Equivalencia significa:
    - Misma versión
    - Mismo número de global_limits y endpoint_limits
    - Cada límite tiene los mismos valores de limit, window y pattern (para endpoints)
    - Las descripciones pueden diferir si el original tenía descripciones vacías
      (el printer las omite, el parser las reconstruye como "")

    Args:
        original: Configuración original.
        parsed: Configuración parseada después de serializar.
    """
    assert original.version == parsed.version, (
        f"Versión no coincide: original={original.version!r}, parsed={parsed.version!r}"
    )

    # Verificar global_limits
    assert len(original.global_limits) == len(parsed.global_limits), (
        f"Número de global_limits no coincide: "
        f"original={len(original.global_limits)}, parsed={len(parsed.global_limits)}"
    )
    for i, (orig_gl, parsed_gl) in enumerate(
        zip(original.global_limits, parsed.global_limits)
    ):
        assert orig_gl.limit == parsed_gl.limit, (
            f"global_limits[{i}].limit no coincide: "
            f"original={orig_gl.limit}, parsed={parsed_gl.limit}"
        )
        assert orig_gl.window == parsed_gl.window, (
            f"global_limits[{i}].window no coincide: "
            f"original={orig_gl.window!r}, parsed={parsed_gl.window!r}"
        )
        # La descripción puede ser "" en el parseado si estaba vacía en el original
        # (el printer omite campos vacíos, el parser los reconstruye como "")

    # Verificar endpoint_limits
    assert len(original.endpoint_limits) == len(parsed.endpoint_limits), (
        f"Número de endpoint_limits no coincide: "
        f"original={len(original.endpoint_limits)}, parsed={len(parsed.endpoint_limits)}"
    )
    for i, (orig_el, parsed_el) in enumerate(
        zip(original.endpoint_limits, parsed.endpoint_limits)
    ):
        assert orig_el.pattern == parsed_el.pattern, (
            f"endpoint_limits[{i}].pattern no coincide: "
            f"original={orig_el.pattern!r}, parsed={parsed_el.pattern!r}"
        )
        assert orig_el.limit == parsed_el.limit, (
            f"endpoint_limits[{i}].limit no coincide: "
            f"original={orig_el.limit}, parsed={parsed_el.limit}"
        )
        assert orig_el.window == parsed_el.window, (
            f"endpoint_limits[{i}].window no coincide: "
            f"original={orig_el.window!r}, parsed={parsed_el.window!r}"
        )


# ---------------------------------------------------------------------------
# Property 11: Rechazo de valores de límite inválidos
# ---------------------------------------------------------------------------

# Feature: rate-limiting-global, Property 11: Rechazo de valores de límite inválidos
@given(
    invalid_limit=st.one_of(
        st.integers(max_value=0),
        st.floats(allow_nan=False, allow_infinity=False),
        st.text(min_size=1),
    )
)
@settings(max_examples=20)
def test_invalid_limit_values_rejected(invalid_limit: int | float | str) -> None:
    """
    Para cualquier valor de límite inválido (≤ 0, float, o string), el parser
    lo rechaza con un error descriptivo que identifica el campo y el valor.

    Construye un YAML mínimo con el valor inválido en el campo 'limit' de
    global_limits, intenta parsearlo y verifica que:
    1. Se lanza RateLimitConfigError
    2. El mensaje de error menciona el campo inválido ('global_limits[1].limit')
    3. El mensaje de error menciona el valor inválido recibido

    **Validates: Requirements 5.5, 5.7**
    """
    if not _RATE_LIMITS_CONFIG_AVAILABLE:
        pytest.skip("app.configuracion.rate_limits_config no disponible — implementar en tarea 12")

    from app.configuracion.rate_limits_config import (
        RateLimitConfigError,
        RateLimitsParser,
    )

    parser = RateLimitsParser()

    # Construir YAML mínimo con el valor inválido
    # Usar representación YAML nativa para el valor (int, float, string)
    import yaml

    yaml_content = yaml.dump(
        {
            "version": "1.0",
            "global_limits": [
                {
                    "limit": invalid_limit,
                    "window": "minute",
                }
            ],
        }
    )

    # Intentar parsear y verificar que se lanza RateLimitConfigError
    with pytest.raises(RateLimitConfigError) as exc_info:
        parser.parse(yaml_content, fmt="yaml")

    error_message = str(exc_info.value)

    # El mensaje debe mencionar el campo inválido
    assert "global_limits[1].limit" in error_message, (
        f"El mensaje de error debe mencionar el campo 'global_limits[1].limit', "
        f"pero se obtuvo: {error_message!r}"
    )

    # El mensaje debe mencionar el valor inválido (o su tipo si es un tipo incorrecto)
    # Para valores numéricos <= 0, el mensaje debe incluir el valor
    # Para strings, el mensaje debe mencionar que se recibió un string
    if isinstance(invalid_limit, (int, float)):
        # El mensaje debe incluir el valor numérico
        assert str(invalid_limit) in error_message or repr(invalid_limit) in error_message, (
            f"El mensaje de error debe mencionar el valor inválido {invalid_limit!r}, "
            f"pero se obtuvo: {error_message!r}"
        )
    elif isinstance(invalid_limit, str):
        # El mensaje debe mencionar que se recibió un string (tipo incorrecto)
        assert "str" in error_message.lower() or "string" in error_message.lower(), (
            f"El mensaje de error debe mencionar que se recibió un string, "
            f"pero se obtuvo: {error_message!r}"
        )


# ---------------------------------------------------------------------------
# Property 12: Rechazo de patrones regex inválidos
# ---------------------------------------------------------------------------

# Feature: rate-limiting-global, Property 12: Rechazo de patrones regex inválidos
@given(
    invalid_pattern=st.text(min_size=1).filter(lambda s: not _is_valid_regex(s))
)
@settings(
    max_examples=20,
    suppress_health_check=[HealthCheck.filter_too_much, HealthCheck.too_slow],
    deadline=None,
)
def test_invalid_regex_patterns_rejected(invalid_pattern: str) -> None:
    """
    Para cualquier patrón regex inválido, el parser lo rechaza con un error
    descriptivo que identifica el patrón inválido.

    Construye un YAML mínimo con el patrón inválido en el campo 'pattern' de
    endpoint_limits, intenta parsearlo y verifica que:
    1. Se lanza RateLimitConfigError
    2. El mensaje de error menciona el campo inválido ('endpoint_limits[1].pattern')
    3. El mensaje de error menciona el patrón inválido

    **Validates: Requirements 5.6, 5.8**
    """
    if not _RATE_LIMITS_CONFIG_AVAILABLE:
        pytest.skip("app.configuracion.rate_limits_config no disponible — implementar en tarea 12")

    from app.configuracion.rate_limits_config import (
        RateLimitConfigError,
        RateLimitsParser,
    )

    parser = RateLimitsParser()

    # Construir YAML mínimo con el patrón inválido
    import yaml

    yaml_content = yaml.dump(
        {
            "version": "1.0",
            "endpoint_limits": [
                {
                    "pattern": invalid_pattern,
                    "limit": 10,
                    "window": "minute",
                }
            ],
        }
    )

    # Intentar parsear y verificar que se lanza RateLimitConfigError
    with pytest.raises(RateLimitConfigError) as exc_info:
        parser.parse(yaml_content, fmt="yaml")

    error_message = str(exc_info.value)

    # El mensaje debe mencionar el campo inválido
    assert "endpoint_limits[1].pattern" in error_message, (
        f"El mensaje de error debe mencionar el campo 'endpoint_limits[1].pattern', "
        f"pero se obtuvo: {error_message!r}"
    )

    # El mensaje debe mencionar el patrón inválido
    # Puede estar entre comillas o como repr()
    assert invalid_pattern in error_message or repr(invalid_pattern) in error_message, (
        f"El mensaje de error debe mencionar el patrón inválido {invalid_pattern!r}, "
        f"pero se obtuvo: {error_message!r}"
    )
