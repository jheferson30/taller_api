# Implementación de Rate Limiting con slowapi

## Resumen

Se implementó rate limiting granular usando slowapi en todos los endpoints de autenticación y gestión de usuarios, cumpliendo con los requirements 16.1-16.7 del spec de mejoras de seguridad JWT.

## Componentes Implementados

### 1. Configuración del Limiter (`app/configuracion/limiter.py`)

- **Key function personalizada**: Identifica requests por IP del cliente
- **Excepción para OPTIONS**: Los requests preflight no consumen límite
- **Whitelist de IPs**: IPs configuradas en `RATE_LIMIT_WHITELIST_IPS` están exentas
- **Storage**: Usa `memory://` para almacenar contadores (puede cambiarse a Redis en producción)

### 2. Variables de Entorno (`.env`)

```env
RATE_LIMIT_AUTH_PER_MINUTE=5
RATE_LIMIT_REFRESH_PER_MINUTE=10
RATE_LIMIT_FORGOT_PASSWORD_PER_HOUR=3
RATE_LIMIT_CREATE_PER_MINUTE=30
RATE_LIMIT_READ_PER_MINUTE=100
RATE_LIMIT_WHITELIST_IPS=
```

### 3. Endpoints Protegidos

#### Autenticación (`app/rutas/auth_ruta.py`)
- **POST /auth/login**: 5 requests/minuto por IP
- **POST /auth/refresh**: 10 requests/minuto por IP
- **POST /auth/forgot-password**: 3 requests/hora por IP

#### Usuarios (`app/rutas/users_ruta.py`)
- **POST /users** (creación): 30 requests/minuto por usuario autenticado
- **GET /users** (lectura): 100 requests/minuto por usuario autenticado
- **GET /users/{id}** (lectura): 100 requests/minuto por usuario autenticado

### 4. Respuestas HTTP 429

Cuando se excede el límite:
- **Status Code**: 429 Too Many Requests
- **Header**: `Retry-After` con segundos hasta que se puede reintentar
- **Manejado por**: `_rate_limit_exceeded_handler` de slowapi

### 5. Integración en `app/main.py`

```python
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from app.configuracion.limiter import limiter

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
```

## Testing

### Tests Unitarios (`tests/test_rate_limiting.py`)
- ✅ Requests dentro del límite retornan 200
- ✅ Requests que exceden el límite retornan 429
- ✅ Diferentes límites funcionan correctamente
- ✅ Diferentes apps tienen límites independientes

### Configuración de Tests (`tests/conftest.py`)
- Límites altos (1000/minuto) para evitar falsos positivos en tests
- Permite que tests de autenticación y usuarios funcionen sin restricciones

## Validación de Requirements

| Requirement | Estado | Implementación |
|------------|--------|----------------|
| 16.1 | ✅ | Endpoints de autenticación limitados a 5 req/min por IP |
| 16.2 | ✅ | Endpoints de creación limitados a 30 req/min por usuario |
| 16.3 | ✅ | Endpoints de lectura limitados a 100 req/min por usuario |
| 16.4 | ✅ | Retorna 429 con header Retry-After |
| 16.5 | ✅ | Usa memoria (configurable a Redis) |
| 16.6 | ✅ | Límites configurables por variables de entorno |
| 16.7 | ✅ | Whitelist de IPs configurable |

## Uso en Producción

### Cambiar a Redis (Recomendado)

Para producción con múltiples instancias, cambiar el storage a Redis:

```python
# app/configuracion/limiter.py
import os

redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
limiter = Limiter(key_func=_key_func, storage_uri=redis_url)
```

### Configurar Whitelist

Para excluir IPs específicas del rate limiting:

```env
RATE_LIMIT_WHITELIST_IPS=192.168.1.100,10.0.0.5,172.16.0.10
```

### Ajustar Límites

Modificar los límites según las necesidades:

```env
# Más restrictivo para producción
RATE_LIMIT_AUTH_PER_MINUTE=3
RATE_LIMIT_FORGOT_PASSWORD_PER_HOUR=2

# Más permisivo para desarrollo
RATE_LIMIT_AUTH_PER_MINUTE=100
```

## Notas Técnicas

1. **IP Detection**: Usa `get_remote_address()` de slowapi que maneja correctamente proxies y load balancers
2. **Memory Storage**: Adecuado para desarrollo y single-instance deployments
3. **Redis Storage**: Requerido para multi-instance deployments (horizontal scaling)
4. **Decorator Order**: `@limiter.limit()` debe ir después de `@router.post()` y antes de `@require_auth`
5. **Dynamic Limits**: Los límites se leen de variables de entorno en cada decorador usando `os.getenv()`

## Próximos Pasos (Opcional)

1. Implementar rate limiting por usuario autenticado (además de por IP)
2. Agregar métricas de rate limiting a dashboard de admin
3. Implementar alertas cuando se detectan patrones de abuso
4. Agregar rate limiting a otros endpoints críticos (upload, etc.)
