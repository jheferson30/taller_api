# Plan de Implementación: Rate Limiting Global

## Resumen

Migrar el rate limiter de `memory://` a Redis, agregar `key_func` dual (IP + usuario JWT),
aplicar `default_limits` global, cubrir los endpoints críticos faltantes con decoradores
`@limiter.limit`, implementar el audit logger estructurado y el módulo de configuración
declarativa con parser/pretty-printer.

El orden sigue la prioridad del documento de requisitos: Crítico → Alto → Medio.

## Tareas

- [x] 1. Actualizar dependencias e infraestructura
  - Agregar `slowapi[redis]` y `fakeredis[aioredis]>=2.0.0` a `requirements.txt`
  - Documentar las nuevas variables `RATE_LIMIT_*` en `.env.example`:
    `REDIS_URL` (ya existe), `RATE_LIMIT_UPLOAD_PER_MINUTE=10`,
    `RATE_LIMIT_WHATSAPP_PER_MINUTE=5`, `RATE_LIMIT_TICKETS_PER_MINUTE=30`,
    `RATE_LIMIT_VEHICULOS_PER_MINUTE=30`, `RATE_LIMIT_USER_PER_MINUTE=200`,
    `RATE_LIMIT_USER_PER_HOUR=2000`
  - _Requisitos: 1.4, 2.1–2.4, 3.2, 3.3_

- [x] 2. Migrar `app/configuracion/limiter.py` a Redis con key_func dual
  - [x] 2.1 Implementar `_get_redis_url()` que lee `REDIS_URL` del entorno (default `redis://redis:6379`)
  - [x] 2.2 Ampliar `_key_func` para extraer `user_id` del JWT cuando el request está autenticado:
    - Si `request.method == "OPTIONS"` → retornar `"options-exempt"`
    - Si la IP está en whitelist → retornar `"whitelist-exempt"`
    - Si `request.state` tiene `user` con `user_id` → retornar `f"user:{user_id}"`
    - Fallback → IP del cliente via `get_remote_address`
  - [x] 2.3 Cambiar `storage_uri="memory://"` por `storage_uri=_get_redis_url()` en el constructor de `Limiter`
  - [x] 2.4 Agregar `default_limits=["100/minute", "1000/hour", "5000/day"]` al constructor de `Limiter`
  - [x] 2.5 Implementar fallback fail-open: si la conexión a Redis falla al inicializar, loguear CRITICAL y crear el limiter con `storage_uri="memory://"` como respaldo
  - _Requisitos: 1.1, 1.2, 1.3, 1.4, 1.6, 1.8, 1.9, 3.1_

- [x] 3. Crear `app/utils/rate_limit_logger.py`
  - [x] 3.1 Implementar `log_rate_limit_violation(*, ip, endpoint, limit_type, limit_value, window, user_agent, timestamp, user_id=None, taller_id=None)` que emite JSON estructurado a `logging.getLogger("rate_limit")` con `severity: "WARNING"`
  - [x] 3.2 Implementar `log_redis_unavailable(error)` que emite JSON con `severity: "CRITICAL"`, `event: "rate_limiter_redis_unavailable"` y `action: "fail_open"`
  - [x] 3.3 Implementar `check_and_alert_high_severity(ip, redis_client)` que:
    - Incrementa el contador `RL_VIOLATIONS:{ip}:5min` en Redis con TTL de 300 s
    - Si el contador supera 10, emite JSON con `severity: "HIGH"` y `event: "rate_limit_high_severity_alert"`
    - Si Redis no está disponible, falla silenciosamente (no bloquea el handler)
  - _Requisitos: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7_

- [x] 4. Reemplazar el handler de `RateLimitExceeded` en `app/main.py`
  - Eliminar la línea `app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)`
  - Registrar un handler personalizado `custom_rate_limit_handler(request, exc)` que:
    1. Extrae IP, endpoint, user_agent y (si existe) user_id/taller_id del request
    2. Llama a `log_rate_limit_violation(...)` con los datos extraídos
    3. Llama a `check_and_alert_high_severity(ip, redis_client)` de forma no bloqueante
    4. Retorna `JSONResponse(status_code=429, content={...}, headers={"Retry-After": str(retry_after)})`
  - El campo `retry_after` se obtiene de `exc.retry_after or 60`
  - _Requisitos: 1.5, 4.1, 4.2, 4.3, 4.4, 4.5, 4.6_

- [x] 5. Checkpoint — infraestructura base lista
  - Verificar que el servidor arranca con `uvicorn app.main:app` sin errores de importación.
  - Verificar que `limiter` se inicializa con Redis (o cae a memory con log CRITICAL si Redis no está).
  - Asegurarse de que todos los tests existentes siguen pasando.

- [x] 6. Aplicar `@limiter.limit` en endpoints críticos
  - [x] 6.1 `app/rutas/upload_ruta.py` — agregar `@limiter.limit(os.getenv("RATE_LIMIT_UPLOAD_PER_MINUTE", "10") + "/minute")` en `POST /upload/foto`, `POST /upload/compra` y `POST /upload/firma`
  - [x] 6.2 `app/rutas/whatsapp_ruta.py` — agregar `@limiter.limit(os.getenv("RATE_LIMIT_WHATSAPP_PER_MINUTE", "5") + "/minute")` en `POST /whatsapp/webhook`, `POST /api/mobile/tickets/{ticket_id}/whatsapp` y `POST /api/whatsapp/tickets/{ticket_id}/mensaje`
  - [x] 6.3 `app/rutas/ticket_ruta.py` — agregar `@limiter.limit(os.getenv("RATE_LIMIT_TICKETS_PER_MINUTE", "30") + "/minute")` en los endpoints `GET /tickets/abiertos`, `GET /tickets/buscar`, `POST /{ticket_id}/procesos`, `POST /{ticket_id}/repuestos`, `POST /{ticket_id}/cobros` y `POST /{ticket_id}/compras`
  - [x] 6.4 `app/rutas/vehiculo_ruta.py` — agregar `@limiter.limit(os.getenv("RATE_LIMIT_VEHICULOS_PER_MINUTE", "30") + "/minute")` en `GET /vehiculos/buscar`, `POST /vehiculos/`, `GET /vehiculos/`, `POST /{placa}/ticket-ingreso`
  - Importar `limiter` desde `app.configuracion.limiter` en cada archivo de ruta donde no esté ya importado
  - _Requisitos: 2.1, 2.2, 2.3, 2.4, 2.6, 2.7_

- [x] 7. Tests unitarios y de propiedades — infraestructura de testing
  - [x] 7.1 Crear `tests/test_rate_limiting_properties.py` con la configuración de Hypothesis:
    - Registrar perfiles `ci` (max_examples=100) y `dev` (max_examples=50)
    - Definir la estrategia `st_rate_limit_config()` para generar `RateLimitConfig` válidos aleatoriamente
    - Definir helper `_is_valid_regex(s)` para filtrar patrones inválidos
  - _Requisitos: 1.1–1.9, 3.1–3.7_

- [x] 8. Tests de propiedades para el limiter (Properties 1–7)
  - [x] 8.1 Property 1 — Enforcement del límite global por IP
    - Usar `fakeredis.FakeRedis()` como backend; crear un `Limiter` con `default_limits=["N/minute"]`
    - Generar con Hypothesis: `ip=st.ip_addresses(v=4).map(str)`, `extra=st.integers(1, 50)`
    - Enviar N+extra requests; verificar que exactamente los primeros N pasan y el resto recibe 429
    - **Property 1: Enforcement del límite global por IP**
    - **Valida: Requisitos 1.1, 1.5**
  - [x] 8.2 Property 2 — Respuesta 429 incluye Retry-After
    - Generar con Hypothesis: `ip=st.ip_addresses(v=4).map(str)`
    - Exceder el límite y verificar que la respuesta 429 contiene el header `Retry-After` con valor entero > 0
    - **Property 2: Respuesta 429 incluye Retry-After**
    - **Valida: Requisito 1.5**
  - [x] 8.3 Property 3 — Whitelist excluye de todos los límites
    - Generar con Hypothesis: `ip=st.ip_addresses(v=4).map(str)`, `count=st.integers(101, 500)`
    - Configurar la IP como whitelist; enviar `count` requests; verificar que todos pasan (nunca 429)
    - **Property 3: Whitelist excluye de todos los límites**
    - **Valida: Requisito 1.8**
  - [x] 8.4 Property 4 — Enforcement de límites por endpoint crítico
    - Generar con Hypothesis: `ip=st.ip_addresses(v=4).map(str)`, `endpoint` de la lista de críticos, `extra=st.integers(1, 20)`
    - Verificar que exactamente los primeros L requests pasan (L = límite del endpoint) y el resto recibe 429
    - **Property 4: Enforcement de límites por endpoint crítico**
    - **Valida: Requisitos 2.1, 2.2, 2.3, 2.4**
  - [x] 8.5 Property 5 — El límite más restrictivo prevalece
    - Generar con Hypothesis: `global_limit=st.integers(10, 200)`, `endpoint_limit=st.integers(1, 200)`
    - Verificar que el número de requests permitidos es `min(global_limit, endpoint_limit)`
    - **Property 5: El límite más restrictivo prevalece**
    - **Valida: Requisitos 2.6, 2.7**
  - [x] 8.6 Property 6 — Extracción correcta del user_id como clave
    - Generar con Hypothesis: `user_id=st.integers(1, 10_000)`, `ip=st.ip_addresses(v=4).map(str)`
    - Crear dos requests con el mismo `user_id` pero diferente IP; verificar que comparten el mismo contador de usuario
    - **Property 6: Extracción correcta del user_id como clave**
    - **Valida: Requisito 3.1**
  - [x] 8.7 Property 7 — Independencia de contadores IP y usuario
    - Generar con Hypothesis: `ip=st.ip_addresses(v=4).map(str)`, `user_id=st.integers(1, 10_000)`
    - Incrementar el contador de IP hasta el límite; verificar que el contador de usuario no se ve afectado y viceversa
    - **Property 7: Independencia de contadores IP y usuario**
    - **Valida: Requisitos 3.4, 3.5, 3.6**

- [x] 9. Tests unitarios del limiter y del handler 429
  - [x] 9.1 `tests/test_limiter_config.py` — smoke test: verificar que `limiter` se inicializa con la URL de Redis correcta (mock de `os.getenv`)
  - [x] 9.2 `tests/test_rate_limit_fail_open.py` — mock de Redis caído: verificar que el request es permitido y que `log_redis_unavailable` es llamado con el error
  - [x] 9.3 `tests/test_rate_limit_options.py` — verificar que requests `OPTIONS` retornan `"options-exempt"` desde `_key_func` y no son limitados
  - [x] 9.4 `tests/test_rate_limit_unauthenticated.py` — verificar que requests sin JWT usan solo el contador de IP (la clave retornada es la IP, no `"user:..."`)
  - _Requisitos: 1.4, 1.6, 1.9, 3.7_

- [x] 10. Checkpoint — rate limiting global y por endpoint funcionando
  - Ejecutar `pytest tests/test_limiter_config.py tests/test_rate_limit_fail_open.py tests/test_rate_limit_options.py tests/test_rate_limit_unauthenticated.py -v`
  - Verificar que los decoradores `@limiter.limit` están presentes en los cuatro archivos de rutas
  - Preguntar al usuario si hay dudas antes de continuar.

- [x] 11. Tests de propiedades para el audit logger (Properties 8–9)
  - [x] 11.1 Property 8 — Estructura completa del log de violación
    - Generar con Hypothesis: `ip=st.ip_addresses(v=4).map(str)`, `user_id=st.one_of(st.none(), st.integers(1, 10_000))`, `endpoint=st.text(min_size=1, max_size=100)`
    - Llamar a `log_rate_limit_violation(...)` y capturar la salida del logger; parsear el JSON y verificar que todos los campos requeridos están presentes con los tipos correctos
    - **Property 8: Estructura completa del log de violación**
    - **Valida: Requisitos 4.1, 4.2, 4.6**
  - [x] 11.2 Property 9 — Alerta HIGH por umbral de violaciones
    - Usar `fakeredis.FakeRedis()` como backend
    - Generar con Hypothesis: `ip=st.ip_addresses(v=4).map(str)`, `violations=st.integers(11, 50)`
    - Llamar a `check_and_alert_high_severity` `violations` veces; verificar que se emite exactamente un log con `severity: "HIGH"` cuando el contador supera 10
    - **Property 9: Alerta HIGH por umbral de violaciones**
    - **Valida: Requisitos 4.3, 4.4**

- [x] 12. Crear `app/configuracion/rate_limits_config.py`
  - [x] 12.1 Definir los dataclasses `GlobalLimit`, `EndpointRateLimit` y `RateLimitConfig` con los campos del diseño
  - [x] 12.2 Implementar `RateLimitConfigError(Exception)` con atributo `line_number: int | None`
  - [x] 12.3 Implementar `RateLimitsParser.parse(content, fmt)`:
    - Parsear YAML o JSON según `fmt`
    - Llamar a `_validate(raw)` antes de construir el objeto
    - Capturar errores de parsing y relanzar como `RateLimitConfigError` con número de línea
  - [x] 12.4 Implementar `RateLimitsParser._validate(raw)`:
    - Verificar que todos los valores de `limit` son enteros > 0; si no, lanzar `RateLimitConfigError` con el campo y valor inválido
    - Verificar que todos los `pattern` son regex válidos con `re.compile`; si no, lanzar `RateLimitConfigError` con el patrón inválido
  - [x] 12.5 Implementar `RateLimitsPrettyPrinter.to_yaml(config)` y `to_json(config)` que serializan `RateLimitConfig` a YAML/JSON válido con indentación
  - _Requisitos: 5.1, 5.2, 5.3, 5.5, 5.6, 5.7, 5.8_

- [x] 13. Tests de propiedades y unitarios para el parser (Properties 10–12)
  - [x] 13.1 Property 10 — Round-trip de configuración declarativa
    - Usar la estrategia `st_rate_limit_config()` definida en la tarea 7.1
    - Serializar con `to_yaml` y `to_json`, luego parsear con `parse`; verificar que el objeto resultante es equivalente al original (mismos patrones y valores de límite)
    - **Property 10: Round-trip de configuración declarativa**
    - **Valida: Requisitos 5.1, 5.3, 5.4**
  - [x] 13.2 Property 11 — Rechazo de valores de límite inválidos
    - Generar con Hypothesis: `invalid_limit=st.one_of(st.integers(max_value=0), st.floats(allow_nan=False, allow_infinity=False), st.text(min_size=1))`
    - Construir un YAML mínimo con ese valor en `limit`; verificar que `parse` lanza `RateLimitConfigError` con mensaje descriptivo que menciona el campo y el valor
    - **Property 11: Rechazo de valores de límite inválidos**
    - **Valida: Requisitos 5.5, 5.7**
  - [x] 13.3 Property 12 — Rechazo de patrones regex inválidos
    - Generar con Hypothesis: `invalid_pattern=st.text(min_size=1).filter(lambda s: not _is_valid_regex(s))`
    - Construir un YAML mínimo con ese patrón en `pattern`; verificar que `parse` lanza `RateLimitConfigError` con mensaje descriptivo que menciona el patrón inválido
    - **Property 12: Rechazo de patrones regex inválidos**
    - **Valida: Requisitos 5.6, 5.8**
  - [x] 13.4 `tests/test_rate_limits_config_examples.py` — ejemplos concretos:
    - Parsear el YAML de ejemplo del diseño y verificar que produce el `RateLimitConfig` esperado
    - Intentar parsear YAML con `limit: 0`, `limit: -5`, `limit: "abc"` y verificar que cada uno lanza `RateLimitConfigError`
    - Intentar parsear YAML con `pattern: "["` (regex inválido) y verificar que lanza `RateLimitConfigError`
    - _Requisitos: 5.1, 5.2, 5.5, 5.6, 5.7, 5.8_

- [x] 14. Checkpoint final — todos los tests pasan
  - Ejecutar `pytest tests/ -v --tb=short` y verificar que no hay fallos.
  - Confirmar que `requirements.txt` y `.env.example` están actualizados.
  - Preguntar al usuario si hay dudas antes de dar por terminada la implementación.

## Notas

- Las tareas marcadas con `*` son opcionales y pueden omitirse para un MVP más rápido.
- Cada tarea referencia los requisitos específicos para trazabilidad.
- Los tests de propiedades usan `fakeredis` para evitar dependencias de infraestructura real.
- El comportamiento fail-open es intencional: un taller no puede quedar sin acceso por un problema de Redis.
- Los decoradores `@limiter.limit` leen los valores desde variables de entorno para permitir ajuste sin cambios de código.
