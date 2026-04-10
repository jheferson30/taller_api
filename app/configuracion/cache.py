"""
Configuración de caché con Redis para FastAPI.

Este módulo inicializa FastAPICache con RedisBackend para cachear
respuestas de endpoints y mejorar el rendimiento del sistema.
"""

import os
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from redis import asyncio as aioredis


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
        redis = aioredis.from_url(
            redis_url,
            encoding="utf-8",
            decode_responses=True
        )
        
        # Inicializar FastAPICache con RedisBackend
        FastAPICache.init(
            RedisBackend(redis),
            prefix="fastapi-cache"
        )
        
        print(f"✓ Caché Redis inicializado correctamente en {redis_url}")
        
    except Exception as e:
        print(f"✗ Error al inicializar caché Redis: {e}")
        raise
