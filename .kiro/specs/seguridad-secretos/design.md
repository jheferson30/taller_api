# Design Document: Seguridad de Secretos

## Overview

Este documento describe la arquitectura técnica para implementar gestión segura de secretos,
encriptación de PII y monitoreo de seguridad en el sistema SaaS multi-tenant de talleres.

El diseño se construye sobre la infraestructura existente (`SecretsManager`, `AuditLogger`,
`tenant_guard.py`, `TokenManager`) y la extiende sin romper contratos actuales.

---

## Architecture

### Diagrama de Componentes

```
┌─────────────────────────────────────────────────────────────────────┐
│                         NUEVOS COMPONENTES                          │
├──────────────────────┬──────────────────────┬───────────────────────┤
│  app/utils/          │  app/servicios/       │  app/seguridad/       │
│  pii_encryptor.py    │  security_alert_      │  token_manager.py     │
│                      │  service.py           │  (extendido)          │
│  scripts/            │                       │                       │
│  secrets_scanner.py  │  app/rutas/           │  app/configuracion/   │
│                      │  super_admin/         │  secrets_manager.py   │
│  app/modelos/        │  seguridad.py         │  (extendido)          │
│  audit_log.py        │                       │                       │
│  (extendido)         │                       │                       │
└──────────────────────┴──────────────────────┴───────────────────────┘
```

### Flujo de Datos — Encriptación PII

```
Cliente HTTP → Ruta → Servicio → Repositorio
                                     │
                                     ▼
                              PII_Encryptor.encrypt()
                                     │
                              ┌──────┴──────┐
                              │  AES-256-GCM │
                              │  IV único    │
                              │  HKDF key    │
                              └──────┬──────┘
                                     │
                                     ▼
                              PostgreSQL (ciphertext)
```

### Flujo de Datos — Rotación JWT

```
TokenManager.decode_token(token)
        │
        ▼
  [clave_actual] → ¿válido? → retornar payload
        │
        ▼ (falla)
  [clave_anterior] → ¿válido? → retornar payload
        │
        ▼ (falla)
  InvalidTokenError
```

### Flujo de Datos — Alertas Cross-Tenant

```
RLS_Guard detecta taller_id incorrecto
        │
        ├─→ AuditLogger.log(SECURITY_ALERT, detalles)
        │
        ├─→ Redis.INCR("CROSS_TENANT:{user_id}", TTL=3600)
        │
        ├─→ ¿contador > 3? → SecurityAlertService.dispatch(HIGH)
        │
        └─→ HTTP 404 al cliente
```

---

## Components

### 1. SecretsManager (extendido)

**Archivo:** `app/configuracion/secrets_manager.py`

**Cambios sobre la versión actual:**
- Agregar `get_jwt_keys() -> list[JWTKeyEntry]` que retorna lista ordenada de claves activas
- Agregar `rotate_jwt_key() -> str` que genera nueva clave, archiva la anterior y registra en audit log
- Agregar `check_rotation_needed() -> bool` que evalúa si la clave activa supera 90 días
- Mantener compatibilidad total con `get_secret()` existente

**Estructura de datos para claves JWT:**

```python
@dataclass
class JWTKeyEntry:
    version: str          # UUID v4 generado al crear la clave
    key: str              # La clave secreta (mínimo 64 chars)
    created_at: datetime  # UTC
    is_active: bool       # True = clave actual para firmar
```

**Fuentes de claves (en orden de prioridad):**
1. Azure Key Vault: secretos `jwt-secret-key` y `jwt-secret-key-previous`
2. Variables de entorno: `JWT_SECRET_KEY` y `JWT_SECRET_KEY_PREVIOUS`
3. Si ninguna disponible → `RuntimeError` al iniciar

**Invariante de rotación:**
- Solo una clave `is_active = True` en cualquier momento
- La clave anterior se retiene durante 7 días (grace period)
- Claves con más de 7 días de antigüedad post-rotación se descartan

---

### 2. TokenManager (extendido)

**Archivo:** `app/seguridad/token_manager.py`

**Cambios sobre la versión actual:**
- Constructor acepta `keys: list[JWTKeyEntry]` además del `secret_key` actual
- `generate_access_token()` y `generate_refresh_token()` firman con la clave `is_active = True`
- El payload incluye `kid` (key version ID) para identificar qué clave usó
- `decode_token()` intenta verificación con cada clave activa en orden descendente de `created_at`
- Mantiene compatibilidad: si se pasa `secret_key` string, funciona igual que antes

**Lógica de decode multi-clave:**

```python
def decode_token(self, token: str) -> dict:
    last_error = None
    for key_entry in sorted(self.keys, key=lambda k: k.created_at, reverse=True):
        try:
            return jwt.decode(token, key_entry.key, algorithms=[self.algorithm])
        except ExpiredSignatureError:
            raise  # expirado es definitivo, no intentar otras claves
        except InvalidTokenError as e:
            last_error = e
            continue
    raise InvalidTokenError(f"Token inválido con todas las claves activas: {last_error}")
```

---

### 3. PII_Encryptor

**Archivo:** `app/utils/pii_encryptor.py`

**Responsabilidad única:** Cifrar y descifrar strings de PII usando AES-256-GCM.

**Diseño de la clave:**
- La `Master_Key` se recupera de `SecretsManager` con nombre `pii-master-key` / env `PII_MASTER_KEY`
- Se deriva una clave de 32 bytes usando HKDF-SHA256 con salt fijo `b"taller-pii-v1"` e info `b"aes-gcm-key"`
- La clave derivada se cachea en memoria (no se re-deriva en cada operación)

**Formato del ciphertext almacenado:**
```
base64( IV(12 bytes) || TAG(16 bytes) || CIPHERTEXT )
```
Todo en un solo campo string para transparencia al esquema de BD.

**Interfaz pública:**

```python
class PIIEncryptor:
    def __init__(self, secrets_manager: SecretsManager): ...

    def encrypt(self, plaintext: str) -> str:
        """Retorna string base64 con IV+TAG+CIPHERTEXT. IV único por llamada."""

    def decrypt(self, ciphertext_b64: str) -> str:
        """Extrae IV, verifica TAG, retorna plaintext. Lanza ValueError si corrupto."""

    def is_encrypted(self, value: str) -> bool:
        """Heurística: detecta si un valor ya está encriptado (para migración)."""
```

**Integración con SQLAlchemy — TypeDecorator:**

```python
class EncryptedString(TypeDecorator):
    """
    Tipo SQLAlchemy que encripta al persistir y desencripta al cargar.
    Transparente para la capa de servicio.
    """
    impl = String
    cache_ok = True

    def process_bind_param(self, value, dialect):
        # Llamado al hacer INSERT/UPDATE
        if value is None:
            return None
        return _encryptor.encrypt(value)

    def process_result_value(self, value, dialect):
        # Llamado al hacer SELECT
        if value is None:
            return None
        return _encryptor.decrypt(value)
```

**Campos afectados en el modelo `Vehiculo`:**
- `nombre_propietario` → `EncryptedString(150)`
- `telefono_propietario` → `EncryptedString(20)`

> **Nota:** El modelo actual usa `Vehiculo` con `nombre_propietario` y `telefono_propietario`.
> No existe un modelo `Cliente` separado. La encriptación aplica a estos campos.
> Si en el futuro se crea un modelo `Cliente`, se aplicará el mismo patrón.

---

### 4. Secrets Scanner

**Archivo:** `scripts/secrets_scanner.py`

**Diseño:** Script Python standalone, sin dependencias del proyecto (solo stdlib).

**Patrones de detección (regex compilados):**

```python
PATTERNS = [
    ("password",    re.compile(r'password\s*=\s*["\'][^"\']{4,}', re.IGNORECASE)),
    ("api_key",     re.compile(r'api[_-]?key\s*=\s*["\'][^"\']{8,}', re.IGNORECASE)),
    ("jwt_secret",  re.compile(r'jwt[_-]?secret\s*=\s*["\'][^"\']{8,}', re.IGNORECASE)),
    ("db_url",      re.compile(r'postgresql://\w+:[^@\s]+@')),
    ("private_key", re.compile(r'-----BEGIN\s+\w*\s*PRIVATE KEY-----')),
]

EXTENSIONS = {".py", ".yaml", ".yml", ".json", ".sh", ".env", ".cfg", ".ini"}

ALLOWLIST = [
    "secrets_scanner.py",   # el propio script contiene los patrones
    ".env.example",         # archivos de ejemplo con valores placeholder
    ".env.test.example",
    ".env.production.example",
]
```

**Salida:**
```
[SECRETS SCANNER] Escaneando 142 archivos...
[FOUND] app/configuracion/base_datos.py:34 — password (password = "123456")
[FOUND] scripts/seed_admin.py:12 — password (password = "admin123")
Total: 2 secreto(s) encontrado(s). Exit code: 1
```

**Integración CI/CD:**
```yaml
# .github/workflows/security.yml (o equivalente)
- name: Secrets Scan
  run: python scripts/secrets_scanner.py
```

---

### 5. RLS_Guard (extendido)

**Archivo:** `app/utils/tenant_guard.py`

**Cambios sobre la versión actual:**
- `verificar_pertenencia()` recibe opcionalmente `request: Request` para poder registrar el evento
- Cuando detecta `objeto.taller_id != taller_id`, antes de lanzar 404:
  1. Llama a `_log_cross_tenant_attempt(request, objeto.taller_id, taller_id)`
  2. Incrementa contador Redis `CROSS_TENANT:{user_id}` con TTL 3600s
  3. Si contador > 3, dispara `SecurityAlertService.dispatch_high_severity()`
- La firma original sin `request` sigue funcionando (retrocompatible)

**Función de logging:**

```python
def _log_cross_tenant_attempt(
    request: Request,
    taller_id_real: int,
    taller_id_solicitado: int,
) -> None:
    """Registra intento cross-tenant en audit log y actualiza contador Redis."""
    audit_repo.create(
        action=AuditAction.SECURITY_ALERT,
        user_id=request.state.user.get("user_id"),
        ip_address=request.client.host,
        user_agent=request.headers.get("user-agent"),
        details={
            "alert_type": "cross_tenant_access_attempt",
            "taller_id_solicitado": taller_id_solicitado,
            "taller_id_real": taller_id_real,
            "endpoint": str(request.url.path),
            "timestamp": datetime.now(UTC).isoformat(),
        },
    )
```

---

### 6. SecurityAlertService

**Archivo:** `app/servicios/security_alert_service.py`

**Responsabilidad:** Despachar alertas a destinos externos (Slack, SMTP, webhook genérico).

**Detección del tipo de destino:**

```python
def _detect_destination_type(url: str) -> Literal["slack", "smtp", "webhook"]:
    if "hooks.slack.com" in url:
        return "slack"
    if url.startswith("smtp://") or url.startswith("smtps://"):
        return "smtp"
    return "webhook"
```

**Severidades:**
- `HIGH`: despacho inmediato (dentro de 60s del evento)
- `LOW`: acumulado en buffer Redis, despachado cada 15 minutos por job

**Retry con backoff exponencial:**

```python
async def _deliver_with_retry(self, payload: dict, url: str) -> None:
    for attempt in range(3):
        try:
            await self._send(payload, url)
            return
        except Exception:
            if attempt < 2:
                await asyncio.sleep(2 ** attempt)  # 1s, 2s
    # Agotados los 3 intentos
    audit_logger.log(AuditAction.SECURITY_ALERT, details={"delivery_failed": True, ...})
```

**Formato Slack (Block Kit):**

```python
{
    "blocks": [
        {"type": "header", "text": {"type": "plain_text", "text": "🚨 Alerta de Seguridad"}},
        {"type": "section", "fields": [
            {"type": "mrkdwn", "text": f"*Tipo:* {event_type}"},
            {"type": "mrkdwn", "text": f"*Severidad:* {severity}"},
            {"type": "mrkdwn", "text": f"*Timestamp:* {timestamp}"},
            {"type": "mrkdwn", "text": f"*Recurso:* {resource_id}"},
        ]},
        {"type": "section", "text": {"type": "mrkdwn", "text": f"*Acción sugerida:* {remediation}"}},
    ]
}
```

---

### 7. Security Dashboard

**Archivo:** `app/rutas/super_admin/seguridad.py`

**Endpoint:** `GET /super-admin/seguridad/metricas`

**Decoradores requeridos:**
```python
@router.get("/super-admin/seguridad/metricas")
@require_auth
@require_role("SUPER_ADMIN")
async def get_security_metrics(request: Request): ...
```

**Fuentes de datos:**
- Rate limit violations → tabla `audit_log` filtrada por `action = SECURITY_ALERT` y `details->alert_type = rate_limit_exceeded`
- Cross-tenant attempts → tabla `audit_log` filtrada por `details->alert_type = cross_tenant_access_attempt`
- Failed auth → tabla `audit_log` filtrada por `action = LOGIN_FAILED`
- Top IPs/users → agregación sobre los mismos registros

**Cache Redis:**
```python
CACHE_KEY = "security_metrics_cache"
CACHE_TTL = 60  # segundos

async def get_security_metrics(request: Request):
    cached = await redis.get(CACHE_KEY)
    if cached:
        return json.loads(cached)
    metrics = await _compute_metrics(db)
    await redis.setex(CACHE_KEY, CACHE_TTL, json.dumps(metrics))
    return metrics
```

**Schema de respuesta:**

```python
class SecurityMetricsResponse(BaseModel):
    rate_limit_violations_24h: list[HourlyCount]      # agrupado por hora
    cross_tenant_attempts_30d: list[DailyCount]        # agrupado por día
    failed_auth_attempts_24h: list[HourlyCount]        # agrupado por hora
    top_ips_by_violations: list[IPViolationEntry]      # top 10
    top_users_by_violations: list[UserViolationEntry]  # top 10
    generated_at: datetime
    cache_hit: bool
```

---

### 8. AuditAction (extendido)

**Archivo:** `app/modelos/audit_log.py`

**Nuevas acciones a agregar:**

```python
class AuditAction(StrEnum):
    # ... existentes ...
    JWT_KEY_ROTATION = "JWT_KEY_ROTATION"
    CROSS_TENANT_ATTEMPT = "CROSS_TENANT_ATTEMPT"
    PII_ACCESS = "PII_ACCESS"
    SECRET_MISSING = "SECRET_MISSING"
    SECURITY_ALERT_DELIVERED = "SECURITY_ALERT_DELIVERED"
    SECURITY_ALERT_FAILED = "SECURITY_ALERT_FAILED"
```

---

### 9. Migración Alembic — PII Encryption

**Archivo:** `alembic/versions/{hash}_encrypt_pii_vehiculos.py`

**Estrategia de migración:**

```python
def upgrade():
    # 1. Agregar columnas temporales encriptadas
    op.add_column("vehiculos", sa.Column("nombre_propietario_enc", sa.String(500)))
    op.add_column("vehiculos", sa.Column("telefono_propietario_enc", sa.String(500)))

    # 2. Migrar datos existentes en lotes de 100
    connection = op.get_bind()
    encryptor = PIIEncryptor(SecretsManager())
    offset = 0
    while True:
        rows = connection.execute(
            "SELECT id, nombre_propietario, telefono_propietario "
            "FROM vehiculos LIMIT 100 OFFSET :offset",
            {"offset": offset}
        ).fetchall()
        if not rows:
            break
        for row in rows:
            connection.execute(
                "UPDATE vehiculos SET nombre_propietario_enc = :n, "
                "telefono_propietario_enc = :t WHERE id = :id",
                {
                    "n": encryptor.encrypt(row.nombre_propietario) if row.nombre_propietario else None,
                    "t": encryptor.encrypt(row.telefono_propietario) if row.telefono_propietario else None,
                    "id": row.id,
                }
            )
        offset += 100

    # 3. Renombrar columnas
    op.drop_column("vehiculos", "nombre_propietario")
    op.drop_column("vehiculos", "telefono_propietario")
    op.alter_column("vehiculos", "nombre_propietario_enc", new_column_name="nombre_propietario")
    op.alter_column("vehiculos", "telefono_propietario_enc", new_column_name="telefono_propietario")


def downgrade():
    # Downgrade requiere desencriptar — solo viable si la Master_Key está disponible
    # En producción, el downgrade de encriptación debe ser una decisión consciente
    raise NotImplementedError(
        "Downgrade de encriptación PII requiere proceso manual controlado. "
        "Ver runbook: docs/runbooks/pii-encryption-rollback.md"
    )
```

---

## Data Models

### Variables de Entorno Nuevas

| Variable | Descripción | Ejemplo |
|---|---|---|
| `JWT_SECRET_KEY_PREVIOUS` | Clave JWT anterior (grace period) | `<64-char-random-string>` |
| `PII_MASTER_KEY` | Clave maestra para derivar claves AES | `<64-char-random-string>` |
| `SECURITY_WEBHOOK_URL` | URL destino para alertas (Slack/webhook) | `https://hooks.slack.com/...` |
| `SECURITY_ALERT_SMTP_HOST` | Host SMTP para alertas por email | `smtp.sendgrid.net` |
| `SECURITY_ALERT_SMTP_PORT` | Puerto SMTP | `587` |
| `SECURITY_ALERT_SMTP_USER` | Usuario SMTP | `apikey` |
| `SECURITY_ALERT_SMTP_PASSWORD` | Contraseña SMTP | `<sendgrid-api-key>` |
| `SECURITY_ALERT_SMTP_FROM` | Dirección remitente | `alertas@taller.app` |
| `SECURITY_ALERT_SMTP_TO` | Destinatario de alertas | `admin@empresa.com` |

Todas deben documentarse en `.env.example` con valores placeholder.

### Redis Keys Nuevas

| Key | Tipo | TTL | Descripción |
|---|---|---|---|
| `CROSS_TENANT:{user_id}` | Counter | 3600s | Intentos cross-tenant por usuario |
| `security_metrics_cache` | String (JSON) | 60s | Cache del dashboard de métricas |
| `security_alerts_low_buffer` | List | 900s | Buffer de alertas LOW pendientes |
| `jwt_key_rotation_lock` | String | 300s | Lock distribuido para rotación JWT |

---

## Error Handling

### Startup Validation

Al iniciar la aplicación (`app/main.py`), se validan todos los secretos requeridos antes de
aceptar requests. Si alguno falta, la app falla con mensaje descriptivo:

```python
def _validate_required_secrets():
    required = [
        ("jwt-secret-key", "JWT_SECRET_KEY"),
        ("pii-master-key", "PII_MASTER_KEY"),
        ("database-password", "DATABASE_PASSWORD"),
    ]
    for secret_name, env_var in required:
        try:
            secrets_manager.get_secret(secret_name, fallback_env_var=env_var)
        except RuntimeError:
            raise RuntimeError(
                f"Secreto requerido no configurado: '{env_var}'. "
                f"Configurar en Azure Key Vault como '{secret_name}' "
                f"o como variable de entorno '{env_var}'."
            )
```

### PII Decryption Failures

Si un campo PII no puede desencriptarse (clave rotada sin migración, datos corruptos):
- `PIIEncryptor.decrypt()` lanza `ValueError` con mensaje genérico
- El repositorio captura y relanza como `HTTPException(500)` con mensaje genérico al cliente
- El detalle completo va al log interno

### Alert Delivery Failures

Si los 3 reintentos de entrega de alerta fallan:
- Se registra en `audit_log` con `AuditAction.SECURITY_ALERT_FAILED`
- La alerta se descarta (no se acumula indefinidamente)
- El sistema continúa operando normalmente

---

## Testing Strategy

### Tests Unitarios

| Componente | Archivo de test | Cobertura mínima |
|---|---|---|
| `PIIEncryptor` | `tests/test_pii_encryptor.py` | Round-trip, IV único, clave inválida |
| `TokenManager` (multi-key) | `tests/test_token_manager.py` | Grace period, clave expirada, sin claves |
| `SecretsManager` (rotación) | `tests/test_secrets_manager.py` | Rotación, grace period, fallo de inicio |
| `SecurityAlertService` | `tests/test_security_alert_service.py` | Slack, webhook, retry, fallo total |
| `RLS_Guard` (extendido) | `tests/test_tenant_guard.py` | Cross-tenant detectado, contador Redis |
| `SecretsScanner` | `tests/test_secrets_scanner.py` | Cada patrón, allowlist, exit codes |

### Property-Based Tests (Hypothesis)

```python
# Property 1: Round-trip PII
@given(st.text(min_size=1, max_size=500))
def test_pii_roundtrip(value):
    encryptor = PIIEncryptor(mock_secrets_manager)
    assert encryptor.decrypt(encryptor.encrypt(value)) == value

# Property 2: IV único por operación
@given(st.text(min_size=1, max_size=500))
def test_pii_unique_ciphertext(value):
    encryptor = PIIEncryptor(mock_secrets_manager)
    c1 = encryptor.encrypt(value)
    c2 = encryptor.encrypt(value)
    assert c1 != c2
    assert encryptor.decrypt(c1) == encryptor.decrypt(c2) == value

# Property 3: JWT grace period
@given(st.dictionaries(st.text(), st.text()))
def test_jwt_grace_period(payload):
    previous_key = JWTKeyEntry(version="v1", key="a"*64, created_at=..., is_active=False)
    current_key  = JWTKeyEntry(version="v2", key="b"*64, created_at=..., is_active=True)
    token = jwt.encode(payload, previous_key.key, algorithm="HS256")
    tm = TokenManager(keys=[current_key, previous_key])
    decoded = tm.decode_token(token)
    assert decoded["user_id"] == payload.get("user_id")
```

---

## Security Checklist

Antes de considerar este spec completo, verificar:

- [ ] `base_datos.py` no tiene `"123456"` como fallback de contraseña
- [ ] `crear_v3.py` y `seed_admin.py` eliminados del repositorio
- [ ] `secrets_scanner.py` pasa sobre el propio codebase sin falsos positivos
- [ ] `PIIEncryptor` usa IV único por operación (verificado con property test)
- [ ] `TokenManager` acepta tokens firmados con clave anterior durante grace period
- [ ] `RLS_Guard` registra en audit log y actualiza contador Redis en cada intento cross-tenant
- [ ] Dashboard `/super-admin/seguridad/metricas` solo accesible con rol `SUPER_ADMIN`
- [ ] Todas las variables de entorno nuevas documentadas en `.env.example`
- [ ] Migración Alembic incluye `upgrade()` completo con migración de datos existentes
- [ ] `SecurityAlertService` registra fallo de entrega en audit log tras 3 reintentos
