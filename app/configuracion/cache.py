"""
Configuración de caché con Redis para FastAPI.

Este módulo inicializa FastAPICache con RedisBackend para cachear
respuestas de endpoints y mejorar el rendimiento del sistema.
"""

import hashlib
import os

from fastapi import Request, Response
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from redis import asyncio as aioredis


def taller_aware_key_builder(
    func,
    namespace: str = "",
    request: Request = None,
    response: Response = None,
    *args,
    **kwargs,
) -> str:
    """
    Key builder para FastAPICache que incluye el taller_id en la clave.

    Garantiza aislamiento multi-tenant: cada taller tiene su propia entrada
    de caché, evitando que un taller vea datos de otro.
    """
    # Obtener taller_id del request state (inyectado por AuthMiddleware)
    taller_id = None
    if request is not None:
        taller_id = getattr(request.state, "taller_id", None)

    # Construir clave base: prefix:namespace:func_name:url_path:query_string
    prefix = FastAPICache.get_prefix()
    url = request.url if request else ""
    cache_key = f"{prefix}:{namespace}:{func.__module__}:{func.__name__}:{url}"

    # Incluir taller_id para aislamiento multi-tenant
    if taller_id is not None:
        cache_key = f"{cache_key}:taller_{taller_id}"

    # Hash para mantener la clave corta
    return hashlib.md5(cache_key.encode()).hexdigest()  # noqa: S324 — no es uso criptográfico


async def init_cache():
    """
    Inicializa el sistema de caché con Redis.

    Lee la URL de Redis desde la variable de entorno REDIS_URL.
    Si no está configurada, usa el valor por defecto: redis://localhost:6379

    Raises:
        Exception: Si no se puede conectar a Redis
    """
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")

    try:
        # Crear conexión a Redis
        redis = aioredis.from_url(redis_url, encoding="utf-8", decode_responses=True)

        # Inicializar FastAPICache con RedisBackend y key_builder multi-tenant
        FastAPICache.init(
            RedisBackend(redis),
            prefix="fastapi-cache",
            key_builder=taller_aware_key_builder,
        )

        print(f"✓ Caché Redis inicializado correctamente en {redis_url}")

    except Exception as e:
        print(f"✗ Error al inicializar caché Redis: {e}")
        raise
