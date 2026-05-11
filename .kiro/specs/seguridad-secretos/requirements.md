# Requirements Document: Seguridad de Secretos

## Introduction

Este documento define los requisitos de gestión segura de secretos, encriptación de PII y monitoreo de seguridad para el sistema SaaS multi-tenant de gestión de talleres mecánicos.

El sistema presenta vulnerabilidades críticas activas: contraseñas hardcodeadas en `base_datos.py` y scripts de inicialización, ausencia de rotación de JWT secrets, datos personales de clientes almacenados en texto plano, y falta de alertas automáticas ante intentos de acceso cross-tenant. Este spec cierra esas brechas de forma sistemática.

**Contexto del Sistema:**
- Backend: FastAPI + PostgreSQL + Redis
- Autenticación: JWT con access/refresh tokens
- Infraestructura existente: `SecretsManager` con soporte Azure Key Vault y fallback a variables de entorno, `AuditLogger` con `AuditAction` tipadas, `Tenant_Repository` con filtrado por `taller_id`

**Alcance:**
Este spec cubre: eliminación de credenciales hardcodeadas, secrets scanning en CI/CD, rotación automática de JWT secret keys, encriptación AES-256-GCM de PII de clientes, alertas de acceso cross-tenant, dashboard de métricas de seguridad para SUPER_ADMIN, e integración con sistemas de alertas externos.

**Relación con otros specs:**
- `seguridad-avanzada`: cubre rate limiting, RLS, CSRF y headers HTTP. Este spec es complementario y no duplica esos requisitos.
- `rate-limiting-global`: cubre contadores de rate limit. Las métricas de rate limiting del dashboard de este spec consumen esos datos.

---

## Glossary

- **Secrets_Manager**: Componente existente en `app/configuracion/secrets_manager.py` que gestiona secretos desde Azure Key Vault con fallback a variables de entorno
- **PII_Encryptor**: Nuevo componente en `app/utils/pii_encryptor.py` que cifra y descifra información personal identificable usando AES-256-GCM
- **JWT_Encoder**: Componente que firma nuevos tokens JWT usando la clave activa más reciente
- **JWT_Decoder**: Componente que verifica tokens JWT intentando todas las claves activas en orden
- **JWT_Secret_Key**: Clave secreta usada para firmar y verificar tokens JWT; puede haber múltiples activas simultáneamente durante el período de gracia
- **JWT_Key_Rotation**: Proceso de reemplazar la JWT_Secret_Key activa por una nueva, manteniendo la anterior durante el grace period
- **Grace_Period**: Período de 7 días tras una rotación durante el cual la clave anterior sigue siendo válida para verificación
- **PII**: Información Personal Identificable — nombres, emails y teléfonos de clientes
- **Master_Key**: Clave maestra almacenada en Secrets_Manager desde la cual se derivan las claves de encriptación de PII
- **IV**: Vector de Inicialización único generado por cada operación de encriptación AES-256-GCM
- **Secrets_Scanner**: Script en `scripts/secrets_scanner.py` que detecta secretos hardcodeados en el codebase
- **Hardcoded_Secret**: Credencial, token, contraseña o clave privada embebida directamente en código fuente o archivos de configuración versionados
- **Cross_Tenant_Access**: Intento de acceder a datos cuyo `taller_id` difiere del `taller_id` del JWT del usuario autenticado
- **RLS_Guard**: Mecanismo que detecta y bloquea intentos de Cross_Tenant_Access
- **Security_Alert_Service**: Nuevo componente en `app/servicios/security_alert_service.py` que envía alertas a destinos externos
- **Security_Dashboard**: Endpoint `GET /super-admin/seguridad/metricas` que expone métricas de seguridad en tiempo real
- **Audit_Logger**: Sistema existente que registra eventos de seguridad usando `AuditAction` tipadas en `app/modelos/audit_log.py`
- **Webhook_URL**: URL configurable via `SECURITY_WEBHOOK_URL` en variables de entorno a la que se envían alertas de seguridad
- **CI_Pipeline**: Pipeline de integración continua que ejecuta validaciones automáticas en cada commit

---

## Requirements

### Requirement 1: Eliminación de Credenciales Hardcodeadas

**User Story:** Como administrador de seguridad, quiero que el sistema no contenga ninguna credencial hardcodeada, para que una exposición del repositorio no comprometa credenciales de producción.

#### Acceptance Criteria

1. THE base_datos.py file SHALL NOT contain any default value for DATABASE_PASSWORD
2. WHEN the DATABASE_PASSWORD environment variable is not set and Azure Key Vault is unavailable, THE application SHALL fail to start with a descriptive error message identifying the missing secret
3. THE crear_v3.py script SHALL be removed from the repository
4. THE seed_admin.py script SHALL be removed from the repository
5. THE codebase SHALL NOT contain any hardcoded API keys, tokens, passwords, or private keys
6. WHEN any required secret is absent from both Secrets_Manager and environment variables, THE application SHALL raise a RuntimeError with the name of the missing secret before accepting any HTTP request
7. THE Secrets_Manager SHALL be the sole mechanism for retrieving secrets — direct calls to `os.getenv` for secrets SHALL only exist as the fallback inside Secrets_Manager itself

---

### Requirement 2: Secrets Scanning en CI/CD

**User Story:** Como administrador de seguridad, quiero escaneo automático de secretos en cada commit, para prevenir que credenciales sean introducidas accidentalmente en el repositorio.

#### Acceptance Criteria

1. THE Secrets_Scanner SHALL be executable both locally and within the CI_Pipeline without additional configuration
2. WHEN the Secrets_Scanner finds a string matching a password pattern (e.g., `password\s*=\s*["'][^"']{4,}`), THE Secrets_Scanner SHALL report the file path and line number
3. WHEN the Secrets_Scanner finds a string matching an API key pattern (e.g., `api[_-]?key\s*=\s*["'][^"']{8,}`), THE Secrets_Scanner SHALL report the file path and line number
4. WHEN the Secrets_Scanner finds a string matching a JWT secret pattern (e.g., `jwt[_-]?secret\s*=\s*["'][^"']{8,}`), THE Secrets_Scanner SHALL report the file path and line number
5. WHEN the Secrets_Scanner finds a database URL containing credentials (e.g., `postgresql://\w+:[^@]+@`), THE Secrets_Scanner SHALL report the file path and line number
6. WHEN the Secrets_Scanner finds a private key block (e.g., `-----BEGIN.*PRIVATE KEY-----`), THE Secrets_Scanner SHALL report the file path and line number
7. THE Secrets_Scanner SHALL scan all files with extensions: `.py`, `.yaml`, `.yml`, `.json`, `.sh`, `.env`, `.cfg`, `.ini`
8. WHEN the Secrets_Scanner detects one or more secrets, THE Secrets_Scanner SHALL exit with a non-zero status code
9. WHEN the Secrets_Scanner finds no secrets, THE Secrets_Scanner SHALL exit with status code 0
10. THE .gitignore file SHALL include patterns to prevent committing `.env`, `.env.local`, `.env.production`, and `.env.*.local` files

---

### Requirement 3: Rotación Automática de JWT Secret Key

**User Story:** Como administrador de seguridad, quiero rotación automática de JWT_Secret_Key cada 90 días, para limitar el impacto de una posible exposición de la clave sin interrumpir sesiones activas.

#### Acceptance Criteria

1. THE Secrets_Manager SHALL support storing and retrieving multiple JWT_Secret_Keys simultaneously, identified by version identifier
2. THE JWT_Encoder SHALL sign all new tokens using the most recently created JWT_Secret_Key
3. THE JWT_Decoder SHALL attempt token verification with each active JWT_Secret_Key in descending order of creation date, accepting the token if any key succeeds
4. THE Secrets_Manager SHALL automatically trigger JWT_Key_Rotation when the current JWT_Secret_Key is older than 90 days
5. WHILE a JWT_Key_Rotation has occurred within the last 7 days, THE Secrets_Manager SHALL retain the previous JWT_Secret_Key as valid for verification (Grace_Period)
6. WHEN a JWT_Key_Rotation occurs, THE Audit_Logger SHALL record an event with action `JWT_KEY_ROTATION`, the key version identifier, and the UTC timestamp
7. THE Secrets_Manager SHALL load JWT_Secret_Keys from environment variables (`JWT_SECRET_KEY`, `JWT_SECRET_KEY_PREVIOUS`) or from Azure Key Vault secrets named `jwt-secret-key` and `jwt-secret-key-previous`
8. WHEN no JWT_Secret_Key is available from any source, THE application SHALL fail to start with a descriptive error message

---

### Requirement 4: Encriptación de PII en Base de Datos

**User Story:** Como administrador de seguridad, quiero que los datos personales de clientes estén encriptados en la base de datos, para que un compromiso de la BD no exponga información personal identificable.

#### Acceptance Criteria

1. THE PII_Encryptor SHALL encrypt the `nombre` field of every Cliente record before persisting to the database
2. THE PII_Encryptor SHALL encrypt the `email` field of every Cliente record before persisting to the database
3. THE PII_Encryptor SHALL encrypt the `telefono` field of every Cliente record before persisting to the database
4. THE PII_Encryptor SHALL use AES-256-GCM as the encryption algorithm for all PII fields
5. THE PII_Encryptor SHALL derive the encryption key from the Master_Key retrieved via Secrets_Manager using HKDF-SHA256
6. THE PII_Encryptor SHALL automatically decrypt PII fields when a Cliente record is loaded from the database, making decryption transparent to the service layer
7. THE PII_Encryptor SHALL generate a unique IV for each individual encryption operation — the same plaintext value encrypted twice SHALL produce different ciphertexts
8. WHEN the Master_Key is not available from Secrets_Manager or environment variables, THE application SHALL fail to start with a clear error message identifying `PII_MASTER_KEY` as the missing secret
9. THE codebase SHALL include an Alembic migration that converts existing plaintext PII fields in the `clientes` table to the encrypted format using the configured Master_Key

---

### Requirement 5: Alertas de Intentos de Acceso Cross-Tenant

**User Story:** Como administrador de seguridad, quiero alertas automáticas cuando un usuario intenta acceder a datos de otro taller, para detectar ataques de escalada de privilegios o bugs de aislamiento multi-tenant.

#### Acceptance Criteria

1. WHEN a database query attempts to access a record whose `taller_id` differs from `request.state.taller_id`, THE RLS_Guard SHALL log a critical security event using `AuditAction.SECURITY_ALERT`
2. THE RLS_Guard SHALL include in the security event log: `user_id`, `taller_id_solicitado`, `taller_id_real`, `endpoint`, and UTC `timestamp`
3. WHEN the same `user_id` has accumulated more than 3 Cross_Tenant_Access attempts within a rolling 1-hour window, THE Security_Alert_Service SHALL dispatch a high-severity alert
4. THE RLS_Guard SHALL block every Cross_Tenant_Access attempt and return HTTP 404 to the client — the response SHALL NOT reveal that the resource exists in another tenant
5. THE cross-tenant security event logs SHALL be retained for a minimum of 90 days
6. THE RLS_Guard SHALL increment a per-user cross-tenant attempt counter stored in Redis with a 1-hour TTL, resetting the counter when the TTL expires

---

### Requirement 6: Dashboard de Métricas de Seguridad para SUPER_ADMIN

**User Story:** Como SUPER_ADMIN, quiero un endpoint de métricas de seguridad en tiempo real, para monitorear el estado de seguridad del sistema sin acceder directamente a la base de datos.

#### Acceptance Criteria

1. THE Security_Dashboard SHALL expose a `GET /super-admin/seguridad/metricas` endpoint
2. THE Security_Dashboard endpoint SHALL be accessible only to authenticated users with the `SUPER_ADMIN` role — any other role SHALL receive HTTP 403
3. THE Security_Dashboard SHALL return rate limit violations grouped by hour for the last 24 hours
4. THE Security_Dashboard SHALL return Cross_Tenant_Access attempts grouped by day for the last 30 days
5. THE Security_Dashboard SHALL return failed authentication attempts grouped by hour for the last 24 hours
6. THE Security_Dashboard SHALL return the top 10 IP addresses ranked by total rate limit violations in the last 24 hours
7. THE Security_Dashboard SHALL return the top 10 user IDs ranked by total rate limit violations in the last 24 hours
8. THE Security_Dashboard SHALL cache its response in Redis for a maximum of 60 seconds — data older than 60 seconds SHALL trigger a cache refresh before responding

---

### Requirement 7: Integración con Sistema de Alertas Externo

**User Story:** Como administrador de seguridad, quiero recibir notificaciones automáticas de eventos críticos de seguridad en Slack o email, para poder responder a incidentes sin monitorear activamente los logs.

#### Acceptance Criteria

1. THE Security_Alert_Service SHALL send alerts to the URL configured in the `SECURITY_WEBHOOK_URL` environment variable
2. WHEN a high-severity security event occurs, THE Security_Alert_Service SHALL deliver the alert to the configured destination within 60 seconds of the event
3. THE Security_Alert_Service SHALL include in every alert payload: event type, severity level, UTC timestamp, affected resource identifier, and a remediation suggestion
4. WHERE the destination is a Slack webhook URL, THE Security_Alert_Service SHALL format the alert payload as a Slack Block Kit message
5. WHERE the destination is an SMTP endpoint (configured via `SECURITY_ALERT_SMTP_*` variables), THE Security_Alert_Service SHALL send the alert as an HTML email
6. WHERE the destination is a generic webhook URL, THE Security_Alert_Service SHALL send the alert as a JSON POST request
7. THE Security_Alert_Service SHALL batch low-severity alerts and dispatch them as a single grouped message every 15 minutes
8. WHEN an alert delivery attempt fails, THE Security_Alert_Service SHALL retry up to 3 times using exponential backoff with initial delay of 1 second, doubling on each retry
9. WHEN all 3 retry attempts are exhausted without success, THE Security_Alert_Service SHALL log the delivery failure using `AuditAction.SECURITY_ALERT` and discard the alert

---

## Correctness Properties for Property-Based Testing

### Property 1: PII Encryption Round-Trip

FOR ALL non-empty string values representing PII (nombres, emails, teléfonos), encrypting the value with PII_Encryptor and then decrypting the result SHALL produce a string equal to the original value.

**Rationale:** AES-256-GCM is an authenticated encryption scheme. Any corruption of the ciphertext, IV, or authentication tag must cause decryption to fail rather than silently return wrong data. This property validates both correctness and integrity.

**Testing approach:** Property-based test using Hypothesis. Generate arbitrary unicode strings of length 1–500 characters. Verify `decrypt(encrypt(value)) == value` for all generated inputs.

### Property 2: JWT Grace Period Verification

FOR ALL tokens signed with a JWT_Secret_Key that was the active key at signing time, WHEN the token is presented to JWT_Decoder within 7 days of a JWT_Key_Rotation that replaced that key, THE JWT_Decoder SHALL successfully verify the token.

**Rationale:** Rotation must not invalidate active user sessions. The grace period ensures continuity. This property validates that the multi-key verification logic correctly handles the transition window.

**Testing approach:** Property-based test using Hypothesis. Generate arbitrary JWT payloads. Sign with a "previous" key. Verify that JWT_Decoder with both current and previous keys accepts the token. Verify that JWT_Decoder with only the current key rejects it.

### Property 3: No Hardcoded Secrets in Codebase

FOR ALL files in the repository with extensions `.py`, `.yaml`, `.yml`, `.json`, `.sh`, `.cfg`, `.ini`, the file content SHALL NOT contain strings matching the secret patterns defined in Secrets_Scanner.

**Rationale:** This property is the automated enforcement of Requirement 1. Running it as a property-based test (or parameterized test over all files) ensures the invariant is continuously verified in CI.

**Testing approach:** Parameterized pytest test. Collect all files matching the target extensions. For each file, assert that none of the Secrets_Scanner patterns match. Fail with file path and line number on first match.

### Property 4: PII Encryption Produces Unique Ciphertexts

FOR ALL non-empty string values representing PII, encrypting the same value twice SHALL produce two different ciphertexts (due to unique IV per operation).

**Rationale:** Deterministic encryption leaks information about repeated values (e.g., two clients with the same email would have identical ciphertext, enabling correlation attacks). This property validates that the IV is truly unique per operation.

**Testing approach:** Property-based test using Hypothesis. Generate arbitrary strings. Encrypt twice. Assert `encrypt(value)[0] != encrypt(value)[0]` (ciphertexts differ) while `decrypt(c1) == decrypt(c2) == value` (both decrypt correctly).
