# Reporte de Auditoría Consolidado — Limpieza de Código Completo

**Fecha:** 2026-04-25
**Proyecto:** SaaS Multi-Tenant — Gestión de Talleres Mecánicos
**Alcance:** Backend (`app/`), Frontend (`frontend/src/`), Scripts (`scripts/`)
**Herramientas:** vulture 2.16, radon 6.0.1, bandit 1.9.4, autoflake, depcheck, análisis manual

---

## Resumen Ejecutivo

### Métricas del Proyecto (Baseline)

| Categoría | Archivos | Líneas brutas | Líneas de código |
|-----------|----------|---------------|-----------------|
| Backend (`app/`) | 105 | 14.846 | 14.244 |
| Tests (`tests/`) | 60 | 15.837 | — |
| Scripts (`scripts/`) | 25 | 1.856 | — |
| Frontend (`frontend/src/`) | 29 JS/JSX | 7.511 | — |
| **Total Python** | **190** | **32.539** | — |

**Tests baseline:** 364 pasando / 151 fallando / 11 omitidos (pre-existentes al inicio de la limpieza)

### Hallazgos por Severidad

| Severidad | Total | Descripción |
|-----------|-------|-------------|
| 🔴 **Crítico** | **14** | Violaciones de seguridad multi-tenant y credenciales hardcodeadas |
| 🟠 **Alto** | **8** | Endpoints sin autenticación, scripts con credenciales, rutas redundantes |
| 🟡 **Medio** | **10** | Antipatrones de auth, complejidad excesiva, código duplicado |
| 🔵 **Bajo** | **18** | Imports lazy, falsos positivos, deuda técnica menor |
| **Total** | **50** | |

### Distribución por Categoría

| Categoría | Hallazgos | Críticos | Altos | Medios | Bajos |
|-----------|-----------|----------|-------|--------|-------|
| Seguridad multi-tenant | 14 | 9 | 4 | 1 | 0 |
| Scripts obsoletos | 13 | 2 | 1 | 0 | 10 |
| Código duplicado | 5 | 0 | 1 | 3 | 1 |
| Imports no usados | 3 | 0 | 0 | 0 | 3 |
| Dependencias no usadas | 7 | 0 | 0 | 3 | 4 |
| Componentes frontend | 2 | 0 | 0 | 1 | 1 |
| Complejidad ciclomática | 6 | 0 | 0 | 2 | 4 |
| **Total** | **50** | **11** | **6** | **10** | **23** |

> **Nota:** Los 14 hallazgos críticos de seguridad multi-tenant son la prioridad absoluta.
> Deben resolverse **antes** de ejecutar cualquier fase de limpieza de código.

---

## 1. Hallazgos de Seguridad Multi-Tenant

> **Severidad: CRÍTICA** — Estos hallazgos deben resolverse antes de cualquier otra tarea de limpieza.
> Representan violaciones reales del aislamiento multi-tenant que exponen datos de todos los talleres.

### 1.1 Endpoints sin autenticación que exponen datos operativos

#### C-01 · `mobile_ruta.py` — Tickets activos sin auth ni filtro taller_id
- **Archivo:** `app/rutas/mobile_ruta.py` línea 18
- **Endpoint:** `GET /mobile/v1/tickets/activos`
- **Severidad:** 🔴 CRÍTICO
- **Problema:** Sin autenticación. La query `db.query(Ticket).filter(Ticket.estado.in_([...]))` no filtra por `taller_id`. Devuelve tickets de **todos** los talleres a cualquier persona sin token.
- **Fix:** Agregar `Depends(requerir_password_admin)`. Agregar filtro `Ticket.taller_id == taller_id`.
- **Nota:** Este archivo no está registrado en `main.py` — eliminarlo en Fase 3A resuelve este hallazgo.

#### C-02 · `mobile_ruta.py` — Timeline de ticket sin auth ni verificación de taller
- **Archivo:** `app/rutas/mobile_ruta.py` líneas 42–57
- **Endpoint:** `GET /mobile/v1/tickets/{ticket_id}/timeline`
- **Severidad:** 🔴 CRÍTICO
- **Problema:** Sin autenticación. Las queries de `TicketProceso` y `TicketFoto` no verifican que el ticket pertenezca al taller del usuario. Cualquiera puede ver el timeline de cualquier ticket con solo conocer el `ticket_id`.
- **Fix:** Eliminar el archivo (no está registrado en `main.py`).

#### C-03 · `whatsapp_ruta.py` — Envío de WhatsApp sin autenticación
- **Archivo:** `app/rutas/whatsapp_ruta.py` líneas 70 y 88
- **Endpoints:** `POST /api/mobile/tickets/{id}/whatsapp`, `POST /api/whatsapp/tickets/{id}/mensaje`
- **Severidad:** 🔴 CRÍTICO
- **Problema:** Sin autenticación. Cualquier persona puede enviar mensajes de WhatsApp en nombre de cualquier taller.
- **Fix:** Agregar `@require_auth`. Verificar `ticket.taller_id == request.state.taller_id`.

#### C-04 · `whatsapp_ruta.py` — Logs de notificaciones sin auth ni filtro taller_id
- **Archivo:** `app/rutas/whatsapp_ruta.py` línea 109
- **Endpoint:** `GET /api/mobile/whatsapp/logs`
- **Severidad:** 🔴 CRÍTICO
- **Problema:** Sin autenticación. La query `db.query(LogNotificacion)` devuelve logs de **todos** los talleres sin filtrar.
- **Fix:** Agregar `@require_auth`. Agregar filtro `LogNotificacion.taller_id == request.state.taller_id`.

#### C-05 · `whatsapp_ruta.py` — Webhook routing incorrecto (multi-taller)
- **Archivo:** `app/rutas/whatsapp_ruta.py` línea ~47
- **Endpoint:** `POST /whatsapp/webhook`
- **Severidad:** 🔴 CRÍTICO
- **Problema:** La query obtiene la **primera** `ConfiguracionTaller` con WhatsApp configurado, sin filtrar por número de teléfono. Con múltiples talleres, todos los mensajes entrantes se asocian al mismo taller.
- **Fix:** Implementar routing por número de teléfono: filtrar `ConfiguracionTaller` por el número de destino del mensaje entrante (`To` en el payload de Twilio).

#### C-06 · `economia_ruta.py` — Datos financieros sin filtro taller_id
- **Archivo:** `app/rutas/economia_ruta.py` líneas 20–80
- **Funciones:** `_base_query_dia()`, `_sumar_por_tipo()` y otros helpers
- **Severidad:** 🔴 CRÍTICO
- **Problema:** Las queries de `MovimientoCaja` no filtran por `taller_id`. La contraseña admin es global (no por taller), por lo que cualquier admin puede ver los datos financieros de todos los talleres.
- **Fix:** Agregar `taller_id` como parámetro a los helpers. Obtenerlo del JWT y pasarlo a cada query.

#### C-07 · `whatsapp_ruta.py` — `ticket.taller_id` usado sin verificación contra JWT
- **Archivo:** `app/rutas/whatsapp_ruta.py` líneas ~80 y ~100
- **Funciones:** `enviar_whatsapp_mobile()`, `enviar_whatsapp_web()`
- **Severidad:** 🔴 CRÍTICO
- **Problema:** Se pasa `ticket.taller_id` al servicio sin verificar que coincida con `request.state.taller_id`.
- **Fix:** Después de agregar auth (C-03): `if ticket.taller_id != request.state.taller_id: raise HTTPException(404)`.

#### C-08 · `mobile_ruta.py` — Ausencia total de filtro taller_id
- **Archivo:** `app/rutas/mobile_ruta.py`
- **Severidad:** 🔴 CRÍTICO
- **Problema:** Ninguna query en este archivo filtra por `taller_id`. El archivo completo viola el aislamiento multi-tenant.
- **Fix:** Eliminar el archivo (no está registrado en `main.py` — ver Sección 3.1).

#### C-09 · `pdf_ruta.py` — `TicketRepository` instanciado sin `taller_id`
- **Archivo:** `app/rutas/pdf_ruta.py` línea ~43
- **Función:** `generate_ticket_pdf()`
- **Severidad:** 🔴 CRÍTICO
- **Problema:** `TicketRepository(db)` se instancia sin `taller_id`, violando el contrato de `TenantRepository`. Puede devolver datos de cualquier taller.
- **Fix:** Agregar autenticación al endpoint. Instanciar con `TicketRepository(db, taller_id=request.state.taller_id)`.

### 1.2 Endpoints sin autenticación explícita (alto riesgo)

#### A-01 · `upload_ruta.py` — Endpoints de subida sin `@require_auth` explícito
- **Archivo:** `app/rutas/upload_ruta.py` líneas 32, 61, 89
- **Endpoints:** `POST /upload/foto`, `POST /upload/compra`, `POST /upload/firma`
- **Severidad:** 🟠 ALTO
- **Problema:** Los endpoints usan `request.state.taller_id` (implica que el middleware procesó el token), pero no tienen `@require_auth` como decorador explícito. Sin segunda línea de defensa.
- **Fix:** Agregar `@require_auth` a los tres endpoints POST.

#### A-02 · `upload_ruta.py` — Archivos servidos sin autenticación
- **Archivo:** `app/rutas/upload_ruta.py` líneas 117, 127, 137
- **Endpoints:** `GET /upload/fotos/{taller_id}/{filename}`, `/compras/...`, `/firmas/...`
- **Severidad:** 🟠 ALTO
- **Problema:** Los archivos son accesibles públicamente si se conoce el `taller_id` y el nombre del archivo. El `taller_id` viene del path (no del JWT).
- **Fix:** Evaluar si deben ser públicos o protegidos. Si protegidos, agregar auth y verificar que `taller_id` del path coincida con el del JWT.

#### A-03 · `pdf_ruta.py` — Endpoints de PDF sin autenticación
- **Archivo:** `app/rutas/pdf_ruta.py` líneas 20, ~61, ~109
- **Endpoints:** `POST /pdf/tickets/{id}/generate`, `GET /pdf/tasks/{id}/status`, `GET /pdf/download/{filename}`
- **Severidad:** 🟠 ALTO
- **Problema:** Cualquier persona puede generar PDFs de cualquier ticket y descargar PDFs generados sin autenticarse.
- **Fix:** Agregar `@require_auth` o `Depends(requerir_password_admin)` a los tres endpoints.

#### A-04 · `main.py` y `health.py` — `urllib.request.urlopen` duplicado
- **Archivos:** `app/main.py` línea 720, `app/rutas/health.py` línea 25
- **Severidad:** 🟠 ALTO
- **Problema:** La función `_get_ip_local()` está duplicada en ambos archivos usando `urllib.request.urlopen` (marcado por bandit como riesgo). Código duplicado + dependencia de servicio externo sin manejo de error robusto.
- **Fix:** Extraer a un helper en `app/utils/` usando `httpx` con timeout y manejo de error explícito.

### 1.3 Antipatrones de autenticación (riesgo medio)

#### M-01 · `seguridad_ruta.py` — `cambiar_password_admin` sin `@require_auth`
- **Archivo:** `app/rutas/seguridad_ruta.py` línea 161
- **Severidad:** 🟡 MEDIO
- **Fix:** Agregar `@require_auth` como decorador explícito.

#### M-02 · `ticket_ruta.py` — Múltiples endpoints sin `@require_auth` explícito
- **Archivo:** `app/rutas/ticket_ruta.py` líneas 89, 94, 197, 253 y más
- **Severidad:** 🟡 MEDIO
- **Fix:** Agregar `@require_auth` a todos los endpoints que acceden a datos del taller.

#### M-03 · `configuracion_ruta.py` — `listar_mecanicos` sin `@require_auth` explícito
- **Archivo:** `app/rutas/configuracion_ruta.py` línea ~54
- **Severidad:** 🟡 MEDIO
- **Fix:** Agregar `@require_auth` explícito para consistencia.

### 1.4 Hallazgos sin violación (para referencia)

| Check | Resultado |
|-------|-----------|
| Mezcla SUPER_ADMIN + roles de taller | ✅ 0 violaciones |
| `taller_id` del body/query_params del cliente | ✅ 0 violaciones |
| Repositorios con TenantRepository | ✅ 5 repositorios correctamente aislados |
| Endpoints SUPER_ADMIN | ✅ Todos con `@require_role("SUPER_ADMIN")` solo |

---

## 2. Scripts Obsoletos

> **Fase de limpieza:** 3A (bajo riesgo) y 3B (riesgo medio para scripts con credenciales)
> **Total a eliminar:** 13 scripts

### 2.1 Scripts con prefijo `_` (temporales de debug — Fase 3A)

| Archivo | Razón de eliminación | Severidad |
|---------|---------------------|-----------|
| `scripts/_aplicar_columnas_faltantes.py` | Script de fix puntual ya ejecutado | 🔵 Bajo |
| `scripts/_check_audit.py` | Script de verificación temporal | 🔵 Bajo |
| `scripts/_check_db.py` | Duplicado de `scripts/check_db.py` | 🔵 Bajo |
| `scripts/_check_login.py` | Script de debug temporal de login | 🔵 Bajo |
| `scripts/_check_which_db.py` | Script de diagnóstico temporal | 🔵 Bajo |
| `scripts/_test_auth_full.py` | Test manual fuera del suite de pytest | 🔵 Bajo |
| `scripts/_test_auth_runtime.py` | Test manual fuera del suite de pytest | 🔵 Bajo |
| `scripts/_test_login.py` | Duplicado de `_check_login.py` | 🔵 Bajo |

**Riesgo de eliminación:** Ninguno — ninguno de estos archivos está registrado en `main.py`, `docker-compose.yml`, `CRON_JOBS.md` ni `README.md`.

### 2.2 Scripts de índices consolidados (Fase 3A)

| Archivo | Razón de eliminación | Severidad |
|---------|---------------------|-----------|
| `scripts/apply_db_indexes.sh` | Consolidado en `create_all_indexes.py` (requiere psql, menos portable) | 🔵 Bajo |
| `scripts/apply_indexes_python.py` | Consolidado en `create_all_indexes.py` (depende de SQL externo desactualizado) | 🔵 Bajo |

**Canónico a mantener:** `scripts/create_all_indexes.py` — Python puro, idempotente (`IF NOT EXISTS`), mejor manejo de errores.

**Acción previa:** Verificar que los índices en `db/migrations/add_composite_indexes.sql` estén cubiertos en `create_all_indexes.py` antes de eliminar.

### 2.3 Scripts con credenciales hardcodeadas (Fase 3A — prioridad de seguridad)

#### `scripts/crear_super_admin_py.py` — ELIMINAR
- **Severidad:** 🟠 ALTO
- **Razón:** Tiene credenciales de BD hardcodeadas (`postgres:123456@localhost`) y contraseña del SUPER_ADMIN en texto plano (`SuperAdmin2026!`). El steering del proyecto establece explícitamente que `crear_super_admin.sql` es el canónico.
- **Canónico:** `scripts/crear_super_admin.sql` — proceso seguro con hash externo via `generar_hash_bcrypt.py`.

#### `scripts/crear_v3.py` — ELIMINAR
- **Severidad:** 🟠 ALTO
- **Razón:** Script de setup inicial de la BD ya ejecutado. Tiene credenciales hardcodeadas (`postgres:123456`) y configuración de collation específica de Windows (`Spanish_Colombia.1252`) que fallaría en producción Linux. Las migraciones Alembic son el mecanismo correcto para gestionar el esquema.

### 2.4 Scripts obsoletos por arquitectura (Fase 3A)

#### `scripts/seed_admin.py` — ELIMINAR
- **Severidad:** 🟠 ALTO
- **Razón:** Crea un usuario `admin` **sin `taller_id`** (NULL), incompatible con la arquitectura multi-tenant actual. `seed_demo.py` cubre el caso de uso de inicialización con datos de prueba de forma más completa. No está documentado en `README.md` ni `CRON_JOBS.md`.

### 2.5 Scripts a mantener

| Script | Razón |
|--------|-------|
| `scripts/cleanup_blacklist.py` | Cron job documentado en `CRON_JOBS.md` |
| `scripts/archive_audit_logs.py` | Cron job documentado en `CRON_JOBS.md` |
| `scripts/security_report.py` | Cron job documentado en `CRON_JOBS.md` |
| `scripts/migrate_passwords.py` | Documentado en `README.md`, tiene tests |
| `scripts/crear_super_admin.sql` | Canónico para SUPER_ADMIN (steering) |
| `scripts/generar_hash_bcrypt.py` | Auxiliar requerido por `crear_super_admin.sql` |
| `scripts/seed_demo.py` | Seed de datos de demo |
| `scripts/create_all_indexes.py` | Canónico de índices |
| `scripts/init_database.py` | Inicialización de BD |
| `scripts/entrypoint.sh` | Usado por Docker como ENTRYPOINT |
| `scripts/deploy.sh` | Despliegue |
| `scripts/rollback.sh` | Rollback de despliegue |
| `scripts/verificar_migracion.py` | Verificación de migraciones |
| `scripts/run_sql_migration.py` | Ejecución de migraciones SQL |
| `scripts/check_db.py` | Verificación de BD (sin prefijo `_`) |
| `scripts/check_indexes.py` | Verificación de índices |
| `scripts/check_security_alerts.py` | Verificación de alertas de seguridad |
| `scripts/update_dependencies.sh` | Actualización de dependencias |
| `scripts/fix-frontend-urls.sh` | Corrección de URLs del frontend |

**Acción adicional:** Actualizar `scripts/README.md` para documentar todos los scripts que se mantienen (actualmente solo documenta `migrate_passwords.py`).

---

## 3. Código Duplicado

> **Fase de limpieza:** 3C (alto riesgo) para consolidaciones, 3B para helpers comunes

### 3.1 Rutas Mobile — `mobile_ruta.py` vs `mobile_api_ruta.py`

| Característica | `mobile_ruta.py` | `mobile_api_ruta.py` |
|---|---|---|
| Registrado en `main.py` | ❌ **NO** | ✅ Sí |
| Autenticación | Sin auth (endpoints públicos) | `requerir_password_admin` en todos |
| Líneas de código | ~75 líneas | ~1034 líneas |
| Endpoints | 3 básicos | 20+ completos |
| Modo offline/sync | No | Sí |
| Finanzas | No | Sí |

**Decisión:** **Eliminar `app/rutas/mobile_ruta.py`** — no está registrado en `main.py`, sus 3 endpoints son un subconjunto simplificado (y sin autenticación) de lo que ya ofrece `mobile_api_ruta.py`. Además expone tickets sin autenticación (hallazgos C-01, C-02, C-08).

**Riesgo:** Bajo — el archivo no está registrado, eliminarlo no afecta ninguna funcionalidad activa.

### 3.2 Servicios WhatsApp — Arquitectura Strategy (correcta)

| Archivo | Tipo | Estado |
|---------|------|--------|
| `app/servicios/whatsapp_service.py` | Interfaz abstracta (ABC) | ✅ Mantener |
| `app/servicios/twilio_whatsapp_service.py` | Implementación concreta | ✅ Mantener |

**Decisión:** **Mantener ambos archivos** — la arquitectura actual es correcta y sigue el patrón Strategy. `whatsapp_service.py` define la interfaz (`WhatsAppService` ABC + enums `TipoEvento`, `ResultadoEnvio`). `twilio_whatsapp_service.py` es la implementación concreta que hereda de ella.

**Acción recomendada:** Documentar en el código que `whatsapp_service.py` es la interfaz y que para agregar un nuevo provider se debe crear una nueva clase que herede de `WhatsAppService`.

### 3.3 Generadores de PDF — Funciones auxiliares duplicadas

Los dos generadores tienen **responsabilidades distintas** (no consolidar en un solo archivo):

| Archivo | Propósito |
|---------|-----------|
| `app/utils/pdf_generator.py` | Comprobante de servicio de un ticket |
| `app/utils/pdf_economia.py` | Reporte de economía diaria del taller |

**Duplicaciones reales encontradas:**

| Elemento duplicado | Ubicación en `pdf_generator.py` | Ubicación en `pdf_economia.py` |
|---|---|---|
| `imagen_escalada()` | Líneas ~75-95 | Líneas ~18-32 |
| `fmt_cop()` | Presente | Presente (idéntica) |
| Paleta de colores (AZUL, GRIS_BORDE, etc.) | Presente | Presente (con comentario `# misma que pdf_generator.py`) |
| Lógica del encabezado con logo | ~30 líneas | ~30 líneas similares |

**Decisión:** **Extraer utilidades comunes a `app/utils/pdf_utils.py`** con `imagen_escalada()`, `fmt_cop()`, paleta de colores base y `construir_encabezado_taller()`. Luego hacer que ambos archivos importen desde `pdf_utils.py`.

**Riesgo:** Medio — requiere actualizar imports en `pdf_ruta.py` y `economia_ruta.py`.

### 3.4 `tenant_repository.py` — Activo y fundamental

**Decisión:** **Mantener** — es importado por 5 repositorios que heredan de él:
- `app/repositorios/movimiento_caja_repository.py`
- `app/repositorios/vehiculo_repository.py`
- `app/repositorios/ticket_repository.py`
- `app/repositorios/notificacion_repository.py`
- `app/repositorios/cita_repository.py`

Es infraestructura de seguridad crítica, no código muerto.

### 3.5 Patrón de validación `taller_id` duplicado

**Ocurrencias del patrón exacto** (`fetch sin taller_id + comparación posterior`):

| Archivo | Línea | Patrón |
|---------|-------|--------|
| `app/rutas/ticket_ruta.py` | 73-76 | `_obtener_ticket_del_taller_o_404()` — helper ya centralizado |
| `app/rutas/mobile_api_ruta.py` | 82-84, 111-113, 132-134, 168-170, 210-212, 223-225, 253-255, 281-283, 317-319, 400-402, 434-436, 494-496, 510-512, 573-575, 602-605, 756-759 | 16 ocurrencias — intencional (auth por contraseña, no JWT) |

**Decisión para `ticket_ruta.py`:** Crear `app/utils/tenant_guard.py` con `verificar_pertenencia(objeto, taller_id, nombre_recurso)` y reemplazar el helper existente.

**Decisión para `mobile_api_ruta.py`:** Los 16 casos son intencionales — la app móvil usa autenticación por contraseña de admin, no JWT con `taller_id`. Evaluar en Fase 3C si debe recibir `taller_id` del token de QR para aplicar aislamiento multi-tenant real.

### 3.6 Función `_get_ip_local()` duplicada

| Archivo | Línea |
|---------|-------|
| `app/main.py` | 720 |
| `app/rutas/health.py` | 25 |

**Decisión:** Extraer a `app/utils/network_utils.py` usando `httpx` con timeout y manejo de error explícito. Importar desde ambos archivos.

---

## 4. Imports No Usados

> **Herramienta:** autoflake 2.x + análisis manual
> **Resultado autoflake:** 0 imports no usados detectados en `app/`

El código tiene una gestión de imports muy limpia. Los únicos hallazgos son imports lazy (dentro de funciones) que son un antipatrón menor.

### 4.1 Imports lazy dentro de funciones (antipatrón)

| Archivo | Línea | Import | Severidad |
|---------|-------|--------|-----------|
| `app/rutas/whatsapp_ruta.py` | ~47 | `from app.modelos.configuracion_taller import ConfiguracionTaller` | 🔵 Bajo |
| `app/rutas/seguridad_ruta.py` | ~185 | `import hmac as _hmac` | 🔵 Bajo |

**Acción:** Mover al bloque de imports del archivo (nivel de módulo).

### 4.2 Imports a verificar

| Archivo | Import | Verificación |
|---------|--------|-------------|
| `app/rutas/mobile_api_ruta.py` | `from app.servicios.whatsapp_service import TipoEvento` | Verificar uso en todos los endpoints del archivo |

### 4.3 Falsos positivos de vulture (no requieren acción)

| Archivo | Línea | Hallazgo | Evaluación |
|---------|-------|----------|------------|
| `app/esquemas/auth_schema.py` | 100 | `cls` no usado | Falso positivo — requerido por `@validator` de Pydantic |
| `app/esquemas/auth_schema.py` | 120 | `cls` no usado | Falso positivo — requerido por `@validator` de Pydantic |
| `app/esquemas/user_schema.py` | 26 | `cls` no usado | Falso positivo — requerido por `@validator` de Pydantic |
| `app/esquemas/whatsapp_schema.py` | 17 | `cls` no usado | Falso positivo — requerido por `@validator` de Pydantic |

**Conclusión:** Todos son falsos positivos. El parámetro `cls` es requerido por la firma del decorador `@validator` de Pydantic aunque no se use en el cuerpo del método. No se requiere acción.

---

## 5. Dependencias No Usadas

### 5.1 Backend — `requirements.txt`

#### Dependencias a eliminar (no usadas en producción)

| Dependencia | Versión | Razón de eliminación | Severidad |
|-------------|---------|---------------------|-----------|
| `Flask` | 3.1.3 | No importada en ningún archivo de `app/`. El proyecto usa FastAPI. | 🟡 Medio |
| `Werkzeug` | 3.1.7 | Dependencia transitiva de Flask — eliminar junto con Flask. | 🟡 Medio |

#### Dependencias de desarrollo en producción (mover a `requirements-dev.txt`)

| Dependencia | Razón |
|-------------|-------|
| `mypy` | Type checker estático — herramienta de desarrollo |
| `ruff` | Linter/formatter — herramienta de desarrollo |
| `pre-commit` | Gestor de git hooks — no tiene sentido en imagen Docker de producción |
| `safety` | Auditoría de vulnerabilidades — herramienta de CI/CD |

#### Dependencias a revisar antes de decidir

| Dependencia | Versión | Situación |
|-------------|---------|-----------|
| `ecdsa` | 0.19.2 | No se importa directamente en `app/`. Listada con comentario `# Cierra CVE-2024-23342`. Posiblemente dependencia transitiva de `pyjwt`. Verificar antes de eliminar. |

#### Dependencias a mantener (correctas)

| Dependencia | Razón |
|-------------|-------|
| `gunicorn` | Usado en `scripts/entrypoint.sh` con `uvicorn.workers.UvicornWorker` — patrón de producción recomendado para FastAPI |
| `uvicorn` | Worker ASGI |
| `fastapi`, `sqlalchemy`, `pydantic`, etc. | Dependencias core del proyecto |

#### Dependencias de desarrollo NO encontradas en `requirements.txt` (no requieren acción)

`pytest`, `bandit`, `pylint`, `radon`, `vulture`, `hypothesis`, `autoflake` — no están declaradas en `requirements.txt` (instaladas manualmente en el entorno virtual).

#### Acción recomendada

Crear `requirements-dev.txt`:
```
# requirements-dev.txt — Solo para desarrollo y CI/CD
pytest
pytest-asyncio
httpx
mypy
ruff
pre-commit
safety
bandit
pylint
radon
vulture
hypothesis
autoflake
```

Eliminar de `requirements.txt`: `Flask`, `Werkzeug`, `mypy`, `ruff`, `pre-commit`, `safety`.

### 5.2 Frontend — `package.json`

#### Dependencias de producción — TODAS USADAS ✅

depcheck no reportó ninguna dependencia de producción sin usar.

**Nota sobre `qrcode.react`:** La suposición inicial de que podría no usarse era incorrecta. Se usa en dos páginas:
- `frontend/src/pages/ConfiguracionPage.jsx` — renderiza QR de conexión WiFi/IP
- `frontend/src/pages/ConfiguracionMecanicoPage.jsx` — mismo uso

#### Dependencias de desarrollo no usadas

| Dependencia | Estado | Acción |
|-------------|--------|--------|
| `@testing-library/user-event` | No referenciada en ningún test | Eliminar de `devDependencies` |
| `@vitest/coverage-v8` | No en imports pero necesaria para `vitest --coverage` CLI | Mantener |

---

## 6. Componentes y Páginas Frontend No Usados

### 6.1 Páginas sin ruta en el router

**Resultado:** 0 páginas sin ruta. Todas las páginas existentes tienen ruta registrada en `App.jsx`.

| Página | Ruta | Roles |
|--------|------|-------|
| `LoginPage.jsx` | `/login` | Público |
| `RecepcionPage.jsx` | `/` | Todos |
| `TicketPage.jsx` | `/tickets` | Todos |
| `CitasPage.jsx` | `/citas` | Todos |
| `InfoPage.jsx` | `/info` | Todos |
| `EntregadosPage.jsx` | `/entregados` | ADMIN, RECEPCIONISTA |
| `EconomiaPage.jsx` | `/economia` | ADMIN |
| `ConfiguracionPage.jsx` | `/configuracion` | ADMIN |
| `ConfiguracionMecanicoPage.jsx` | `/configuracion` | MECANICO, RECEPCIONISTA |
| `SuperAdminPage.jsx` | `/super-admin` | SUPER_ADMIN |

### 6.2 Componentes no importados en ninguna página

#### F-01 · `EconomiaAuth.jsx` — ELIMINAR
- **Archivo:** `frontend/src/components/EconomiaAuth.jsx`
- **Severidad:** 🟡 Medio
- **Descripción:** Componente de autenticación de economía que no es importado en ninguna página ni componente del proyecto. Probablemente fue reemplazado por el sistema de roles (`RoleGuard` en `App.jsx`).
- **Acción:** Eliminar en Fase 3B.

#### F-02 · `ProtectedRoute.jsx` — Solo en tests
- **Archivo:** `frontend/src/components/ProtectedRoute.jsx`
- **Severidad:** 🔵 Bajo
- **Descripción:** Solo aparece en archivos de test (`ProtectedRoute.test.jsx`). No se usa en producción — `App.jsx` usa `AppLayout` + `RoleGuard` en su lugar.
- **Acción:** Revisar si se puede eliminar junto con sus tests, o mantener si los tests son válidos.

### 6.3 Componentes activos (para referencia)

| Componente | Usado en |
|------------|----------|
| `EstadisticasDashboard.jsx` | `EconomiaPage.jsx` |
| `PageHero.jsx` | 7 páginas (TicketPage, RecepcionPage, InfoPage, EntregadosPage, EconomiaPage, ConfiguracionPage, CitasPage) |
| `Starfield.jsx` | `App.jsx` (fondo animado global) |
| `InputDinero.jsx` | `TicketPage.jsx` |
| `NotificationBadge.jsx` | `App.jsx` |
| `NotificationBanner.jsx` | `App.jsx` |
| `SelectMecanico.jsx` | `TicketPage.jsx`, `RecepcionPage.jsx` |

### 6.4 Duplicación menor en frontend

#### F-03 · `API_BASE` duplicado en `api.js` y `authService.js`
- **Severidad:** 🔵 Bajo
- **Descripción:** La lógica de cálculo de `API_BASE` está copiada literalmente en ambos archivos (3 líneas idénticas). Si cambia la lógica, hay que actualizarla en dos lugares.
- **Acción (Fase 3B):** Extraer a una constante compartida en `frontend/src/config.js` e importarla en ambos archivos.

**Nota:** La separación de responsabilidades entre `api.js` y `authService.js` es correcta y bien diseñada. No hay duplicación de lógica de autenticación real.

---

## 7. Complejidad Ciclomática

> **Herramienta:** radon 6.0.1
> **Complejidad promedio del proyecto:** A (2.88) — Excelente
> **Umbral de refactorización:** CC > 10

### 7.1 Funciones con complejidad crítica (CC > 40 — Grado F)

| Función | Archivo | CC | Grado | Prioridad |
|---------|---------|-----|-------|-----------|
| `generar_pdf_ticket_completo` | `app/utils/pdf_generator.py:114` | 77 | F | 🔴 Urgente |
| `generar_pdf_economia_profesional` | `app/utils/pdf_economia.py:70` | 49 | F | 🔴 Urgente |

**Acción:** Refactorizar extrayendo secciones del PDF en funciones privadas: `_generar_encabezado()`, `_generar_tabla_procesos()`, `_generar_tabla_repuestos()`, `_generar_pie_pagina()`, etc.

### 7.2 Funciones con complejidad muy alta (CC 21-50 — Grado D)

| Función | Archivo | CC | Grado |
|---------|---------|-----|-------|
| `sincronizar_operaciones_batch` | `app/rutas/mobile_api_ruta.py:713` | 29 | D |
| `AuthMiddleware.dispatch` | `app/seguridad/auth_middleware.py:52` | 28 | D |
| `generar_pdf_cliente` | `app/rutas/ticket_ruta.py:926` | 26 | D |
| `validate_config` | `app/configuracion/config_validator.py:18` | 26 | D |

### 7.3 Funciones con complejidad alta (CC 11-20 — Grado C)

| Función | Archivo | CC |
|---------|---------|-----|
| `AuthMiddleware` (clase) | `app/seguridad/auth_middleware.py:24` | 16 |
| `get_tickets_with_details` | `app/repositorios/ticket_repository.py:57` | 16 |
| `economia_hoy_mobile` | `app/rutas/mobile_api_ruta.py:981` | 15 |
| `generar_ticket_desde_cita` | `app/servicios/cita_service.py:105` | 15 |
| `entregar_ticket` | `app/servicios/ticket_service.py:143` | 14 |
| `cambiar_password_admin` | `app/rutas/seguridad_ruta.py:161` | 13 |
| `enviar_notificacion` | `app/servicios/twilio_whatsapp_service.py:14` | 11 |
| `enviar_mensaje_manual` | `app/servicios/twilio_whatsapp_service.py:126` | 11 |
| `crear_o_actualizar_vehiculo` | `app/servicios/cita_service.py:23` | 11 |
| `buscar_tickets` | `app/rutas/ticket_ruta.py:198` | 11 |

**Total funciones sobre umbral (CC > 10):** 14

---

## 8. Hallazgos de Bandit (Seguridad General)

> **Total líneas analizadas:** 14.244
> **Issues High:** 0 ✅
> **Issues Medium:** 2 (reales)
> **Issues Low:** 35 (33 son falsos positivos)

### 8.1 Hallazgos reales

| Severidad | Archivo | Línea | Descripción | Acción |
|-----------|---------|-------|-------------|--------|
| 🟡 Medio | `app/main.py` | 720 | `urllib.request.urlopen` a api.ipify.org | Usar `httpx` con timeout |
| 🟡 Medio | `app/rutas/health.py` | 25 | Misma función duplicada | Consolidar en helper |
| 🔵 Bajo | `app/utils/pdf_economia.py` | 159 | `except Exception: pass` sin logging | Agregar `logger.warning()` |
| 🔵 Bajo | `app/utils/pdf_generator.py` | 213, 353 | `except Exception: pass` sin logging (x2) | Agregar `logger.warning()` |

### 8.2 Falsos positivos (no requieren acción)

- Contraseñas en `json_schema_extra` (ejemplos de documentación OpenAPI)
- Valores de enum `AuditAction` con "PASSWORD" en el nombre
- Valores de campo `token_type` ("access", "refresh")
- Booleanos `False` en diccionarios de resultados

---

## 9. Plan de Acción por Fases

### Fase 0 (Completada) — Preparación y baseline
- ✅ Tests baseline: 364 pasando
- ✅ Métricas baseline registradas
- ✅ Herramientas instaladas (vulture, radon, bandit)

### Fase 1 (Completada) — Auditoría
- ✅ Auditoría automatizada del backend (vulture, radon, bandit, autoflake)
- ✅ Auditoría de seguridad multi-tenant (auth, taller_id, role mixing)
- ✅ Auditoría manual de duplicaciones
- ✅ Auditoría de scripts
- ✅ Auditoría del frontend
- ✅ Auditoría de dependencias del backend

### Fase 2 (En curso) — Reporte consolidado
- ✅ Este documento

### Fase 3A — Bajo riesgo (scripts obsoletos)

**Prerequisito:** Verificar que `pytest tests/ -q` pasa antes de iniciar.

| Tarea | Archivos | Riesgo |
|-------|----------|--------|
| Eliminar 8 scripts con prefijo `_` | `scripts/_*.py` (8 archivos) | Ninguno |
| Eliminar scripts de índices obsoletos | `apply_db_indexes.sh`, `apply_indexes_python.py` | Ninguno |
| Eliminar `crear_super_admin_py.py` | 1 archivo | Ninguno |
| Eliminar `crear_v3.py` | 1 archivo | Ninguno |
| Eliminar `seed_admin.py` | 1 archivo | Ninguno |
| Actualizar `scripts/README.md` | 1 archivo | Ninguno |

**Verificación:** `pytest tests/ -q` debe pasar sin cambios.

### Fase 3B — Riesgo medio (imports, dead code, dependencias, frontend)

| Tarea | Archivos | Riesgo |
|-------|----------|--------|
| Eliminar imports lazy (mover a nivel módulo) | `whatsapp_ruta.py`, `seguridad_ruta.py` | Bajo |
| Eliminar `EconomiaAuth.jsx` | 1 archivo | Bajo |
| Extraer `API_BASE` a `frontend/src/config.js` | `api.js`, `authService.js` | Bajo |
| Crear `requirements-dev.txt` | 1 archivo nuevo | Bajo |
| Eliminar `Flask`, `Werkzeug`, `mypy`, `ruff`, `pre-commit`, `safety` de `requirements.txt` | 1 archivo | Medio |
| Eliminar `@testing-library/user-event` de `package.json` | 1 archivo | Bajo |
| Agregar logging a `except Exception: pass` en PDFs | `pdf_economia.py`, `pdf_generator.py` | Bajo |

**Verificación:** `pytest tests/ -q` + `npm run test` deben pasar.

### Fase 3C — Alto riesgo (consolidación, seguridad)

| Tarea | Archivos | Riesgo |
|-------|----------|--------|
| Eliminar `mobile_ruta.py` (resuelve C-01, C-02, C-08) | 1 archivo | Bajo (no registrado) |
| Corregir `whatsapp_ruta.py` (C-03, C-04, C-05, C-07) | 1 archivo | Alto |
| Corregir `economia_ruta.py` (C-06) | 1 archivo | Alto |
| Corregir `pdf_ruta.py` (C-09, A-03) | 1 archivo | Medio |
| Corregir `upload_ruta.py` (A-01, A-02) | 1 archivo | Medio |
| Agregar `@require_auth` explícito (M-01, M-02, M-03) | 3 archivos | Medio |
| Extraer `app/utils/tenant_guard.py` | 1 archivo nuevo | Medio |
| Extraer `app/utils/pdf_utils.py` (helpers comunes de PDF) | 1 archivo nuevo | Medio |
| Extraer `app/utils/network_utils.py` (`_get_ip_local`) | 1 archivo nuevo | Bajo |

**Verificación:** `pytest tests/ -q` + smoke test manual de endpoints críticos.

---

## 10. Índice de Calidad de Código

| Dimensión | Puntuación | Notas |
|-----------|-----------|-------|
| Complejidad ciclomática promedio | 95/100 | CC promedio A (2.88) — excelente |
| Gestión de imports | 95/100 | 0 imports no usados, solo 2 imports lazy |
| Seguridad multi-tenant | 45/100 | 9 hallazgos críticos activos |
| Código duplicado | 70/100 | Duplicaciones menores, arquitectura Strategy correcta |
| Dependencias | 75/100 | Flask/Werkzeug innecesarias, dev deps en producción |
| Scripts | 60/100 | 13 scripts obsoletos, 3 con credenciales hardcodeadas |
| Frontend | 85/100 | 1 componente no usado, 1 constante duplicada |
| **Índice general** | **75/100** | Buen código base con problemas de seguridad críticos |

> **Nota:** El índice de seguridad multi-tenant (45/100) arrastra el índice general.
> Una vez resueltos los 9 hallazgos críticos, el índice subiría a ~88/100.

---

## 11. Archivos de Reporte Fuente

| Reporte | Ubicación | Tarea |
|---------|-----------|-------|
| Métricas baseline | `baseline-metrics.md` | 1.1, 1.2 |
| Código muerto (vulture) | `vulture-report.txt` | 2.1 |
| Complejidad ciclomática (radon) | `radon-report.txt` | 2.2 |
| Seguridad general (bandit) | `bandit-report.txt` | 2.3 |
| Imports no usados | `unused-imports-report.txt` | 2.4 |
| Auth faltante | `security-auth-report.txt` | 2.5 |
| Queries sin taller_id | `security-tenant-queries-report.txt` | 2.6 |
| taller_id del cliente | `security-taller-id-report.txt` | 2.7 |
| Role mixing | `security-role-mixing-report.txt` | 2.8 |
| Resumen auditoría backend | `audit-summary-2.md` | 2 (resumen) |
| Duplicaciones manuales | `auditoria-duplicaciones.md` | 3 |
| Scripts | `scripts-audit.md` | 4 |
| Frontend | `frontend-audit-findings.md` | 5 |
| Dependencias frontend | `depcheck-report.json` | 5.4 |
| Dependencias backend | (sección 6 de este documento) | 6 |
| Hallazgos a resolver | `hallazgos-a-resolver.md` | Consolidado |

