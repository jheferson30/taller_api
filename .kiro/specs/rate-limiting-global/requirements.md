# Requirements Document: Rate Limiting Global

## Introduction

Este documento define los requisitos para implementar rate limiting robusto y completo en el sistema SaaS multi-tenant de gestión de talleres mecánicos.

El sistema actualmente tiene SlowAPI instalado pero con storage en memoria (`memory://`) y cobertura parcial (~20% de endpoints). Esto significa que los contadores se resetean al reiniciar el servidor, no hay límite global, y endpoints críticos como `/upload/*`, `/whatsapp/*`, `/tickets`, `/vehiculos`, `/clientes` y `/citas` operan sin ninguna protección.

**Estado actual:**
- `app/configuracion/limiter.py` usa `storage_uri="memory://"`
- Redis ya está disponible en la infraestructura Docker (`redis:6379`)
- Variables de entorno existentes: `RATE_LIMIT_AUTH_PER_MINUTE`, `RATE_LIMIT_CREATE_PER_MINUTE`, `RATE_LIMIT_READ_PER_MINUTE`, `RATE_LIMIT_WHITELIST_IPS`
- Solo ~20% de endpoints tienen `@limiter.limit` aplicado

**Archivos afectados:**
- `app/configuracion/limiter.py` — cambiar storage a Redis, agregar key_func por usuario
- `app/main.py` — agregar `default_limits` global
- `app/rutas/upload_ruta.py` — agregar `@limiter.limit`
- `app/rutas/whatsapp_ruta.py` — agregar `@limiter.limit`
- `app/rutas/ticket_ruta.py` — agregar `@limiter.limit`
- `app/rutas/vehiculo_ruta.py` — agregar `@limiter.limit`
- `app/configuracion/rate_limits_config.py` — nuevo, parser de configuración declarativa
- `.env.example` — nuevas variables `RATE_LIMIT_*`
- `requirements.txt` — verificar `slowapi[redis]` o `redis-py`

## Glossary

- **Rate_Limiter**: Componente basado en SlowAPI que controla la frecuencia de requests por IP o usuario autenticado para prevenir abuso y ataques DDoS
- **Redis_Store**: Instancia de Redis usada como backend persistente para almacenar contadores de rate limiting; disponible en `redis:6379` en la infraestructura Docker
- **IP_Key**: Identificador de rate limiting basado en la dirección IP del cliente, extraída del header `X-Forwarded-For` o la conexión directa
- **User_Key**: Identificador de rate limiting basado en el `user_id` extraído del JWT cuando el request está autenticado
- **Rate_Window**: Ventana de tiempo fija (minuto, hora, día) dentro de la cual se cuentan los requests para aplicar el límite
- **Rate_Limit_Config**: Objeto que representa la configuración declarativa de límites por endpoint, parseado desde un archivo YAML o JSON
- **Rate_Limits_Parser**: Componente que parsea archivos de configuración YAML/JSON de rate limits y los valida
- **Rate_Limits_Pretty_Printer**: Componente que serializa un `Rate_Limit_Config` de vuelta a un archivo YAML/JSON válido
- **Audit_Logger**: Sistema de logging estructurado en formato JSON que registra eventos de rate limiting para análisis y alertas
- **Critical_Endpoint**: Endpoint que maneja operaciones costosas o sensibles: `/upload/*`, `/whatsapp/*`, `/tickets`, `/vehiculos`, `/clientes`, `/citas`
- **Whitelist_IP**: Dirección IP excluida de rate limiting, configurada en `RATE_LIMIT_WHITELIST_IPS` (por defecto: `127.0.0.1`, `::1`)
- **Fail_Open**: Comportamiento del Rate_Limiter cuando Redis_Store no está disponible — permite el request en lugar de bloquearlo, y registra el error

## Requirements

### Requirement 1: Rate Limiting Global por IP con Storage Redis

**User Story:** Como administrador del sistema, quiero que todos los endpoints tengan un límite global de requests por IP respaldado por Redis, para prevenir ataques DDoS y abuso incluso después de reinicios del servidor.

#### Acceptance Criteria

1. THE Rate_Limiter SHALL enforce a global limit of 100 requests per minute per IP_Key on all endpoints
2. THE Rate_Limiter SHALL enforce a global limit of 1000 requests per hour per IP_Key on all endpoints
3. THE Rate_Limiter SHALL enforce a global limit of 5000 requests per day per IP_Key on all endpoints
4. THE Rate_Limiter SHALL use Redis_Store as the backend storage for all rate limit counters
5. WHEN an IP_Key exceeds any rate limit, THE Rate_Limiter SHALL return HTTP 429 with a `Retry-After` header indicating the seconds until the Rate_Window resets
6. WHEN the Redis_Store is unavailable, THE Rate_Limiter SHALL apply Fail_Open behavior and log a critical error via Audit_Logger
7. FOR ALL IP_Key values and Rate_Window boundaries, THE Rate_Limiter SHALL reset the counter to zero exactly at the window boundary
8. THE Rate_Limiter SHALL exclude Whitelist_IP addresses from all rate limit checks
9. THE Rate_Limiter SHALL exclude HTTP OPTIONS requests from all rate limit checks

### Requirement 2: Rate Limiting Específico por Endpoint

**User Story:** Como administrador del sistema, quiero aplicar límites más estrictos en endpoints críticos y un límite por defecto en todos los demás, para proteger recursos costosos y garantizar cobertura total.

#### Acceptance Criteria

1. WHEN a request targets an endpoint matching `/upload/*`, THE Rate_Limiter SHALL enforce a limit of 10 requests per minute per IP_Key
2. WHEN a request targets an endpoint matching `/whatsapp/*`, THE Rate_Limiter SHALL enforce a limit of 5 requests per minute per IP_Key
3. WHEN a request targets the `/tickets` endpoint, THE Rate_Limiter SHALL enforce a limit of 30 requests per minute per IP_Key
4. WHEN a request targets the `/vehiculos` endpoint, THE Rate_Limiter SHALL enforce a limit of 30 requests per minute per IP_Key
5. WHEN a request targets a Critical_Endpoint without an explicit rate limit declaration, THE Rate_Limiter SHALL enforce a default limit of 20 requests per minute per IP_Key
6. WHEN multiple rate limits apply to a single request, THE Rate_Limiter SHALL apply the most restrictive limit
7. THE Rate_Limiter SHALL apply endpoint-specific limits in addition to, not instead of, the global IP limits from Requirement 1

### Requirement 3: Rate Limiting por Usuario Autenticado

**User Story:** Como administrador del sistema, quiero aplicar rate limiting por usuario autenticado además de por IP, para prevenir abuso de cuentas comprometidas independientemente de la IP de origen.

#### Acceptance Criteria

1. WHEN a request includes a valid JWT token, THE Rate_Limiter SHALL extract the `user_id` from the token payload and use it as the User_Key
2. THE Rate_Limiter SHALL enforce a limit of 200 requests per minute per User_Key
3. THE Rate_Limiter SHALL enforce a limit of 2000 requests per hour per User_Key
4. THE Rate_Limiter SHALL apply IP_Key limits and User_Key limits independently and simultaneously
5. WHEN the IP_Key limit is exceeded, THE Rate_Limiter SHALL return HTTP 429 regardless of the User_Key counter
6. WHEN the User_Key limit is exceeded, THE Rate_Limiter SHALL return HTTP 429 regardless of the IP_Key counter
7. WHEN a request does not include a JWT token, THE Rate_Limiter SHALL apply only IP_Key limits

### Requirement 4: Logging Estructurado de Eventos de Rate Limiting

**User Story:** Como administrador de seguridad, quiero logging detallado y estructurado de todas las violaciones de rate limiting, para detectar patrones de ataque y realizar análisis forense.

#### Acceptance Criteria

1. WHEN an IP_Key exceeds a rate limit, THE Audit_Logger SHALL emit a JSON log entry containing: `ip`, `endpoint`, `limit_type`, `limit_value`, `window`, `user_agent`, and `timestamp`
2. WHEN a User_Key exceeds a rate limit, THE Audit_Logger SHALL emit a JSON log entry containing: `user_id`, `taller_id`, `endpoint`, `limit_type`, `limit_value`, `window`, `user_agent`, and `timestamp`
3. THE Audit_Logger SHALL aggregate rate limit violations by IP_Key over 5-minute windows
4. WHEN an IP_Key accumulates more than 10 rate limit violations within a 5-minute window, THE Audit_Logger SHALL emit a high-severity alert log entry with `severity: "HIGH"` and the aggregated violation count
5. THE Audit_Logger SHALL include the `User-Agent` header value in all rate limit log entries
6. THE Audit_Logger SHALL emit all rate limit log entries in structured JSON format
7. WHEN the Redis_Store is unavailable and Fail_Open behavior is triggered, THE Audit_Logger SHALL emit a critical log entry with `severity: "CRITICAL"` and the Redis connection error details

### Requirement 5: Parser y Pretty Printer para Configuración Declarativa de Rate Limits

**User Story:** Como administrador del sistema, quiero parsear y serializar archivos de configuración de rate limits en YAML o JSON, para gestionar los límites por endpoint de forma declarativa sin modificar código.

#### Acceptance Criteria

1. WHEN a valid rate limits configuration file is provided, THE Rate_Limits_Parser SHALL parse it into a `Rate_Limit_Config` object containing endpoint patterns and their associated limits
2. WHEN an invalid rate limits configuration file is provided, THE Rate_Limits_Parser SHALL return a descriptive error message that includes the line number of the first invalid entry
3. THE Rate_Limits_Pretty_Printer SHALL format a `Rate_Limit_Config` object back into a valid YAML or JSON configuration file
4. FOR ALL valid `Rate_Limit_Config` objects, parsing then printing then parsing SHALL produce an equivalent object (round-trip property)
5. THE Rate_Limits_Parser SHALL validate that all rate limit values are positive integers greater than zero
6. THE Rate_Limits_Parser SHALL validate that all endpoint patterns are valid regular expressions
7. WHEN a rate limit value is zero, negative, or non-integer, THE Rate_Limits_Parser SHALL return a descriptive error identifying the invalid field and its value
8. WHEN an endpoint pattern is not a valid regular expression, THE Rate_Limits_Parser SHALL return a descriptive error identifying the invalid pattern

## Correctness Properties for Property-Based Testing

### Property 1: Rate Limiting Enforcement (Propiedad de Invariante)

FOR ALL IP_Key values and Rate_Window boundaries, WHEN the number of requests from an IP_Key within a Rate_Window exceeds the configured limit, THEN all subsequent requests from that IP_Key within the same Rate_Window SHALL be rejected with HTTP 429 until the window resets.

**Tipo:** Invariante — el sistema nunca debe permitir más requests que el límite configurado dentro de una ventana.
**Candidato PBT:** Sí — el comportamiento varía con el número de requests, el límite configurado y el timing de la ventana. 100 iteraciones con distintos límites y conteos encontrarán edge cases que 2-3 ejemplos no detectarían.

### Property 2: Exactitud del Contador de Rate Limit (Propiedad Metamórfica)

FOR ALL IP_Key values and Rate_Window boundaries, THE rate limit counter stored in Redis_Store SHALL equal the actual number of requests made by that IP_Key within the current Rate_Window.

**Tipo:** Metamórfica — la relación entre requests enviados y contador almacenado debe ser exacta.
**Candidato PBT:** Sí — varía con el número de requests concurrentes y secuenciales. Detecta race conditions que ejemplos fijos no cubren.

### Property 3: Round-Trip de Configuración de Rate Limits (Propiedad Round-Trip)

FOR ALL valid `Rate_Limit_Config` objects, parsing then printing then parsing SHALL produce an object equivalent to the original, where equivalence means identical endpoint patterns and limit values.

**Tipo:** Round-trip — parsear → imprimir → parsear debe producir el mismo objeto.
**Candidato PBT:** Sí — esencial para parsers. 100 iteraciones con configuraciones generadas aleatoriamente detectarán casos de serialización incorrecta que ejemplos manuales no cubren.

## Priority Classification

### Crítico (Implementar Primero)
- Requirement 1: Rate Limiting Global por IP con Storage Redis
- Requirement 2: Rate Limiting Específico por Endpoint

### Alto (Implementar Segundo)
- Requirement 3: Rate Limiting por Usuario Autenticado
- Requirement 4: Logging Estructurado de Eventos de Rate Limiting

### Medio (Implementar Tercero)
- Requirement 5: Parser y Pretty Printer para Configuración Declarativa de Rate Limits
