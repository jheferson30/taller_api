# Tasks: Seguridad de Secretos

- [x] 1. Extender AuditAction con nuevas acciones tipadas
  - Archivo: `app/modelos/audit_log.py`
  - Requisitos: 3.6, 5.1, 7.9
  - Agregar al enum `AuditAction`:
    - `JWT_KEY_ROTATION` — rotación de clave JWT
    - `CROSS_TENANT_ATTEMPT` — intento de acceso cross-tenant
    - `PII_ACCESS` — acceso a datos PII desencriptados
    - `SECRET_MISSING` — secreto requerido no encontrado al iniciar
    - `SECURITY_ALERT_DELIVERED` — alerta externa entregada exitosamente
    - `SECURITY_ALERT_FAILED` — alerta externa fallida tras 3 reintentos
  - Este task es prerequisito de todos los demás

- [x] 2. Eliminar credenciales hardcodeadas y agregar validación de secretos al startup
  - Archivos: `app/configuracion/base_datos.py`, `app/main.py`, `scripts/crear_v3.py` (eliminar), `scripts/seed_admin.py` (eliminar), `.env.example`
  - Requisitos: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7
  - [x] 2.1. Limpiar `base_datos.py`: en `_get_database_url()`, eliminar el fallback hardcodeado `"123456"`. Si `SecretsManager` y `DATABASE_PASSWORD` fallan, relanzar `RuntimeError` descriptivo
  - [x] 2.2. Eliminar `scripts/crear_v3.py` y `scripts/seed_admin.py` del repositorio
  - [x] 2.3. En `app/main.py`, agregar `_validate_required_secrets()` que se ejecuta en el evento `startup` verificando: `jwt-secret-key`, `pii-master-key`, `database-password`
  - [x] 2.4. Documentar en `.env.example`: `JWT_SECRET_KEY_PREVIOUS`, `PII_MASTER_KEY`, `SECURITY_WEBHOOK_URL`, variables `SECURITY_ALERT_SMTP_*`

- [x] 3. Implementar Secrets Scanner
  - Archivos: `scripts/secrets_scanner.py`, `.gitignore`
  - Requisitos: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8, 2.9, 2.10
  - [x] 3.1. Crear `scripts/secrets_scanner.py` (solo stdlib): patrones `password`, `api_key`, `jwt_secret`, `db_url`, `private_key`; extensiones `.py .yaml .yml .json .sh .env .cfg .ini`; allowlist con archivos de ejemplo; salida `[FOUND] ruta:linea — tipo (fragmento)`; exit 1 si hay hallazgos
  - [x] 3.2. Verificar y agregar en `.gitignore`: `.env`, `.env.local`, `.env.production`, `.env.*.local`

- [x] 4. Extender SecretsManager con soporte multi-clave JWT y rotación
  - Archivo: `app/configuracion/secrets_manager.py`
  - Requisitos: 3.1, 3.4, 3.5, 3.6, 3.7, 3.8
  - [x] 4.1. Agregar dataclass `JWTKeyEntry` con campos: `version` (UUID v4), `key` (min 64 chars), `created_at` (UTC datetime), `is_active` (bool)
  - [x] 4.2. Agregar método `get_jwt_keys() -> list[JWTKeyEntry]`: carga desde Key Vault (`jwt-secret-key`, `jwt-secret-key-previous`) o env (`JWT_SECRET_KEY`, `JWT_SECRET_KEY_PREVIOUS`); incluir clave anterior solo si está dentro del grace period de 7 días
  - [x] 4.3. Agregar método `check_rotation_needed() -> bool`: retorna True si la clave activa tiene más de 90 días
  - [x] 4.4. Agregar método `rotate_jwt_key() -> str`: genera nueva clave con `secrets.token_hex(32)`, archiva la actual como `previous`, registra `AuditAction.JWT_KEY_ROTATION`, usa lock Redis `jwt_key_rotation_lock` (TTL 300s)

- [x] 5. Extender TokenManager con verificación multi-clave
  - Archivo: `app/seguridad/token_manager.py`
  - Requisitos: 3.2, 3.3
  - [x] 5.1. Actualizar constructor para aceptar `keys: list[JWTKeyEntry] | None = None`; mantener compatibilidad con `secret_key` string
  - [x] 5.2. Actualizar `generate_access_token()` y `generate_refresh_token()` para firmar con la clave `is_active=True` e incluir `kid` en el payload
  - [x] 5.3. Actualizar `decode_token()`: iterar claves por `created_at` descendente; relanzar `ExpiredSignatureError` inmediatamente; relanzar último `InvalidTokenError` si todas fallan
  - [x] 5.4. Tests unitarios en `tests/test_token_manager.py`: clave activa, clave anterior en grace period, clave anterior fuera de grace period, token expirado, sin claves, property test grace period (Hypothesis)

- [x] 6. Implementar PIIEncryptor con AES-256-GCM
  - Archivo: `app/utils/pii_encryptor.py`
  - Requisitos: 4.4, 4.5, 4.6, 4.7, 4.8
  - [x] 6.1. Implementar clase `PIIEncryptor`: `__init__` deriva clave AES con HKDF-SHA256 desde `PII_MASTER_KEY`; `encrypt` genera IV único de 12 bytes y retorna `base64(IV || TAG || CIPHERTEXT)`; `decrypt` extrae IV+TAG+CIPHERTEXT y lanza `ValueError` si TAG no coincide; `is_encrypted` heurística para migración
  - [x] 6.2. Implementar `EncryptedString` TypeDecorator SQLAlchemy: `process_bind_param` encripta, `process_result_value` desencripta, singleton `_get_encryptor()`
  - [x] 6.3. Tests unitarios en `tests/test_pii_encryptor.py`: round-trip, IV único, corrupción → ValueError, clave inválida → RuntimeError, property tests Hypothesis (Properties 1 y 4)

- [x] 7. Aplicar EncryptedString al modelo Vehiculo
  - Archivo: `app/modelos/vehiculo.py`
  - Requisitos: 4.1, 4.2, 4.3, 4.6
  - Cambiar `nombre_propietario` y `telefono_propietario` de `String` a `EncryptedString(500)`
  - Agregar comentario en cada columna explicando encriptación AES-256-GCM transparente

- [x] 8. Crear migración Alembic para encriptar PII existente
  - Archivo: `alembic/versions/{hash}_encrypt_pii_vehiculos.py`
  - Requisito: 4.9
  - `upgrade()`: agregar columnas temporales `_enc`, migrar datos en lotes de 100 con `PIIEncryptor` (None → None, ya encriptado → copiar, plaintext → encriptar), eliminar originales, renombrar `_enc`
  - `downgrade()`: lanza `NotImplementedError` con mensaje de proceso manual requerido

- [x] 9. Extender RLS_Guard con detección y logging de intentos cross-tenant
  - Archivo: `app/utils/tenant_guard.py`
  - Requisitos: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6
  - [x] 9.1. Agregar función interna `_log_cross_tenant_attempt(request, taller_id_real, taller_id_solicitado)`: registra en audit log con `AuditAction.SECURITY_ALERT`, incrementa contador Redis `CROSS_TENANT:{user_id}` (TTL 3600), dispara alerta HIGH si contador > 3
  - [x] 9.2. Actualizar `verificar_pertenencia()` con parámetro opcional `request: Request | None = None`; llamar `_log_cross_tenant_attempt()` antes del 404
  - [x] 9.3. Actualizar `obtener_recurso_del_taller()` con mismo patrón, propagando `request`
  - [x] 9.4. Tests unitarios en `tests/test_tenant_guard.py`: acceso correcto, cross-tenant sin request, cross-tenant con request, 4to intento → alerta HIGH, objeto sin taller_id

- [x] 10. Implementar SecurityAlertService
  - Archivo: `app/servicios/security_alert_service.py`
  - Requisitos: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7, 7.8, 7.9
  - [x] 10.1. Implementar clase `SecurityAlertService` con métodos: `dispatch_high_severity`, `enqueue_low_severity`, `flush_low_severity_buffer`, `_detect_destination_type`, `_format_slack`, `_format_email`, `_deliver_with_retry`
  - [x] 10.2. Implementar `_deliver_with_retry()`: 3 intentos con backoff 1s/2s; si todos fallan, registrar `AuditAction.SECURITY_ALERT_FAILED` y descartar
  - [x] 10.3. Implementar formato Slack Block Kit: header 🚨, campos Tipo/Severidad/Timestamp/Recurso, sección Acción sugerida
  - [x] 10.4. Implementar formato email HTML con `aiosmtplib` usando variables `SECURITY_ALERT_SMTP_*`
  - [x] 10.5. Tests unitarios en `tests/test_security_alert_service.py`: Slack, webhook, retry exitoso, retry fallido → SECURITY_ALERT_FAILED, buffer LOW, sin SECURITY_WEBHOOK_URL → solo warning

- [x] 11. Implementar job de rotación JWT y flush de alertas LOW
  - Archivo: `app/jobs/security_jobs.py`
  - Requisitos: 3.4, 7.7
  - [x] 11.1. Job `check_jwt_rotation`: diario; si `check_rotation_needed()` → `rotate_jwt_key()`; loguear resultado
  - [x] 11.2. Job `flush_security_alerts`: cada 15 minutos; `flush_low_severity_buffer()`; no hacer nada si buffer vacío
  - Integrar con scheduler existente o usar `asyncio.create_task` en evento `startup`

- [x] 12. Implementar Security Dashboard
  - Archivos: `app/rutas/super_admin/seguridad.py`, `app/esquemas/seguridad_metricas.py`, `app/repositorios/security_metrics_repository.py`
  - Requisitos: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7, 6.8
  - [x] 12.1. Crear schemas Pydantic en `app/esquemas/seguridad_metricas.py`: `HourlyCount`, `DailyCount`, `IPViolationEntry`, `UserViolationEntry`, `SecurityMetricsResponse`
  - [x] 12.2. Crear `app/repositorios/security_metrics_repository.py`: queries sobre `audit_log` para rate limit violations 24h, cross-tenant 30d, failed auth 24h, top IPs, top users
  - [x] 12.3. Crear `app/rutas/super_admin/seguridad.py`: `GET /super-admin/seguridad/metricas` con `@require_auth` + `@require_role("SUPER_ADMIN")`, cache Redis TTL 60s
  - [x] 12.4. Registrar el nuevo router en `app/main.py`

- [x] 13. Agregar dependencias nuevas a requirements.txt
  - Archivo: `requirements.txt`
  - Requisitos: 4.4, 7.5
  - Verificar y agregar si faltan: `cryptography==42.0.8`, `aiosmtplib==3.0.1`, `aiohttp==3.9.5`

- [x] 14. Ejecutar Secrets Scanner y verificar limpieza del codebase
  - Requisitos: 1.5, 2.1, Property 3
  - Ejecutar `python scripts/secrets_scanner.py` y corregir todos los hallazgos
  - El scanner debe salir con código 0 antes de considerar el spec completo
  - Depende de Task 2 y Task 3

- [x] 15. Tests de integración y property-based tests
  - Archivos: `tests/test_pii_encryptor.py`, `tests/test_token_manager.py`, `tests/test_secrets_scanner.py`
  - Requisitos: Properties 1, 2, 3, 4
  - [x] 15.1. Property 1 — PII Round-Trip: `@given(st.text(min_size=1, max_size=500))` → `decrypt(encrypt(value)) == value`
  - [x] 15.2. Property 2 — JWT Grace Period: firmar con clave anterior, verificar con TokenManager con ambas claves; verificar que solo clave actual rechaza el token
  - [x] 15.3. Property 3 — No Hardcoded Secrets: `@pytest.mark.parametrize` sobre todos los archivos target; fallar con ruta y línea si hay match
  - [x] 15.4. Property 4 — PII Unique Ciphertexts: `encrypt(v) != encrypt(v)` y ambos decriptan igual
  - Verificar que todos los tests pasan con `pytest tests/ -x`
