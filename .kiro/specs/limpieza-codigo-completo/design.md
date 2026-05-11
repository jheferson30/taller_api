# Design Document — Limpieza de Código Completo

## Overview

Este documento describe el diseño técnico para ejecutar la auditoría exhaustiva y limpieza del código del sistema SaaS de gestión de talleres mecánicos. El enfoque es **pragmático y directo**: analizar el código real que existe hoy, identificar problemas concretos, y ejecutar la limpieza en fases ordenadas por riesgo.

El proceso se divide en tres etapas:
1. **Auditoría** — análisis estático del código existente con herramientas y revisión manual
2. **Reporte** — documentación de todos los hallazgos con severidad y ubicación exacta
3. **Limpieza** — ejecución por fases, de menor a mayor riesgo, con tests de regresión entre cada fase

---

## Architecture

### Estructura actual del proyecto

```
taller_api_v3/
├── app/
│   ├── configuracion/     # base_datos, cache, config_validator, limiter, secrets_manager
│   ├── esquemas/          # Pydantic schemas (10 archivos)
│   ├── modelos/           # SQLAlchemy models (23 archivos)
│   ├── repositorios/      # DB queries (12 archivos)
│   ├── rutas/             # FastAPI routers (19 archivos)
│   ├── seguridad/         # JWT, middleware, hashing (4 archivos)
│   ├── servicios/         # Business logic (13 archivos)
│   ├── tasks/             # Celery tasks (3 archivos)
│   ├── utils/             # Helpers (5 archivos)
│   └── main.py
├── frontend/src/
│   ├── components/        # 9 componentes React
│   ├── pages/             # 10 páginas React
│   ├── services/          # authService.js
│   ├── api.js
│   └── App.jsx
├── scripts/               # 33 scripts (varios obsoletos con prefijo _)
├── tests/                 # Suite de tests
└── migrations/            # Migraciones Alembic
```

### Flujo de la auditoría

```
┌─────────────────────────────────────────────────────────┐
│                    FASE 0: PREPARACIÓN                   │
│  git checkout -b limpieza-codigo-$(date +%Y%m%d)        │
│  pytest → baseline de tests pasando                      │
└─────────────────────┬───────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────┐
│                  FASE 1: AUDITORÍA                       │
│  Backend: vulture + pylint + bandit + radon              │
│  Frontend: eslint + depcheck                             │
│  Manual: scripts/, tests/, migrations/, config           │
└─────────────────────┬───────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────┐
│                   FASE 2: REPORTE                        │
│  auditoria-report.md con hallazgos por severidad         │
│  plan-limpieza.md con acciones priorizadas               │
└─────────────────────┬───────────────────────────────────┘
                      │
        ┌─────────────┼─────────────┐
        ▼             ▼             ▼
┌───────────┐  ┌───────────┐  ┌───────────┐
│  FASE 3A  │  │  FASE 3B  │  │  FASE 3C  │
│ Bajo      │  │  Medio    │  │  Alto     │
│ Riesgo    │  │  Riesgo   │  │  Riesgo   │
│ scripts_  │  │ imports,  │  │ código    │
│ obsoletos │  │ dead code │  │ duplicado │
└───────────┘  └───────────┘  └───────────┘
```

---

## Components and Interfaces

### Componente 1: Analizador de Scripts Obsoletos

**Objetivo:** Identificar y eliminar los scripts con prefijo `_` y otros scripts temporales.

**Scripts identificados para eliminación (prefijo `_` = temporales de debug):**
```
scripts/_aplicar_columnas_faltantes.py   → ELIMINAR (script de fix puntual ya aplicado)
scripts/_check_audit.py                  → ELIMINAR (script de verificación temporal)
scripts/_check_db.py                     → ELIMINAR (duplicado de scripts/check_db.py)
scripts/_check_login.py                  → ELIMINAR (script de debug de login)
scripts/_check_which_db.py               → ELIMINAR (script de diagnóstico temporal)
scripts/_test_auth_full.py               → ELIMINAR (test manual, no es parte del suite)
scripts/_test_auth_runtime.py            → ELIMINAR (test manual, no es parte del suite)
scripts/_test_login.py                   → ELIMINAR (duplicado de _check_login.py)
```

**Scripts a revisar (posible duplicación):**
```
scripts/check_db.py          vs  scripts/_check_db.py     → mantener check_db.py
scripts/seed_admin.py        vs  scripts/seed_demo.py     → revisar si seed_admin.py sigue siendo necesario
scripts/crear_super_admin_py.py  vs  scripts/crear_super_admin.sql → el .sql es el canónico (ver steering)
scripts/crear_v3.py          → revisar si es script de migración ya ejecutado
scripts/apply_db_indexes.sh  vs  scripts/apply_indexes_python.py  vs  scripts/create_all_indexes.py → 3 scripts para lo mismo
```

**Scripts a mantener (documentados en README.md o CRON_JOBS.md):**
```
scripts/crear_super_admin.sql     → canónico para crear SUPER_ADMIN
scripts/seed_demo.py              → seed de datos de demo
scripts/init_database.py          → inicialización de BD
scripts/cleanup_blacklist.py      → cron job documentado
scripts/archive_audit_logs.py     → cron job documentado
scripts/security_report.py        → utilidad de seguridad
scripts/entrypoint.sh             → usado por Docker
scripts/deploy.sh                 → despliegue
scripts/rollback.sh               → rollback de despliegue
```

### Componente 2: Analizador de Código Muerto (Backend)

**Herramienta principal:** `vulture` — detecta funciones, clases y variables no usadas.

**Configuración de vulture** (`vulture.toml`):
```toml
[tool.vulture]
min_confidence = 80
paths = ["app/"]
exclude = [
    "app/modelos/",        # SQLAlchemy models usan atributos dinámicamente
    "migrations/",
    "app/tasks/",          # Celery tasks se registran dinámicamente
]
ignore_names = [
    "setUp", "tearDown",   # pytest fixtures
    "model_*",             # Pydantic validators
]
```

**Áreas de riesgo conocidas:**
- `app/rutas/mobile_ruta.py` y `app/rutas/mobile_api_ruta.py` — dos archivos para mobile, posible duplicación
- `app/servicios/whatsapp_service.py` y `app/servicios/twilio_whatsapp_service.py` — dos servicios de WhatsApp
- `app/utils/pdf_generator.py` y `app/utils/pdf_economia.py` — dos generadores de PDF
- `app/repositorios/tenant_repository.py` — repositorio de tenant separado, verificar si se usa

**Imports no usados — patrón común a buscar:**
```python
# Patrón frecuente en rutas: importar schemas que no se usan en ese archivo
from app.esquemas.ticket_schema import TicketCreate, TicketUpdate, TicketResponse  # ¿se usan todos?
```

### Componente 3: Analizador de Duplicación (Backend)

**Duplicaciones de alta probabilidad identificadas:**

#### 3.1 Dos servicios de WhatsApp
```
app/servicios/whatsapp_service.py        → servicio original
app/servicios/twilio_whatsapp_service.py → servicio con Twilio
```
**Decisión:** Mantener solo el que esté activo según la variable de entorno `WHATSAPP_PROVIDER`. Consolidar en un único `whatsapp_service.py` con estrategia de provider.

#### 3.2 Dos rutas de mobile
```
app/rutas/mobile_ruta.py     → ruta original de mobile
app/rutas/mobile_api_ruta.py → ruta API de mobile
```
**Decisión:** Revisar si ambas están registradas en `main.py`. Si una no está registrada, eliminarla.

#### 3.3 Dos generadores de PDF
```
app/utils/pdf_generator.py   → generador genérico
app/utils/pdf_economia.py    → generador específico de economía
```
**Decisión:** Mantener ambos si tienen responsabilidades distintas. Si `pdf_generator.py` es un wrapper de `pdf_economia.py`, consolidar.

#### 3.4 Tres scripts de índices de BD
```
scripts/apply_db_indexes.sh
scripts/apply_indexes_python.py
scripts/create_all_indexes.py
```
**Decisión:** Mantener solo `create_all_indexes.py` (Python, más portable). Eliminar los otros dos.

#### 3.5 Validación de taller_id duplicada
Patrón a buscar en servicios: lógica de verificación de pertenencia al taller repetida en múltiples servicios en lugar de estar en un helper centralizado.

```python
# Patrón duplicado (aparece en múltiples servicios):
ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
if not ticket or ticket.taller_id != taller_id:
    raise HTTPException(status_code=404)
```
**Decisión:** Extraer a `app/utils/tenant_guard.py` con función `verificar_pertenencia(objeto, taller_id)`.

### Componente 4: Analizador de Frontend

**Herramienta:** ESLint con reglas `no-unused-vars` y `import/no-unused-modules`.

**Componentes a verificar:**
```
frontend/src/components/EconomiaAuth.jsx      → ¿importado en alguna página?
frontend/src/components/EstadisticasDashboard.jsx → ¿importado en alguna página?
frontend/src/components/PageHero.jsx          → ¿importado en alguna página?
frontend/src/components/Starfield.jsx         → ¿importado en alguna página?
```

**Páginas a verificar contra el router en App.jsx:**
```
frontend/src/pages/InfoPage.jsx               → ¿tiene ruta en App.jsx?
frontend/src/pages/EntregadosPage.jsx         → ¿tiene ruta en App.jsx?
```

**api.js vs authService.js:**
- `frontend/src/api.js` — cliente HTTP base
- `frontend/src/services/authService.js` — servicio de autenticación
- Verificar que no haya lógica de auth duplicada entre ambos archivos.

### Componente 5: Analizador de Dependencias

**Backend — dependencias a revisar en `requirements.txt`:**

| Dependencia | Uso esperado | Verificar |
|-------------|-------------|-----------|
| `Flask==3.1.3` | No debería estar — proyecto es FastAPI | ¿Se usa en algún archivo? |
| `Werkzeug==3.1.7` | Dependencia de Flask | Eliminar si Flask se elimina |
| `ecdsa==0.19.2` | Criptografía | ¿Se importa directamente? |
| `safety==3.7.0` | Análisis de seguridad | Solo dev, no producción |
| `mypy==1.20.2` | Type checking | Solo dev, no producción |
| `pre-commit` | Git hooks | Solo dev, no producción |
| `gunicorn` | WSGI server | ¿Se usa con uvicorn? |
| `nltk` | NLP | ¿Se usa en el proyecto? |

**Frontend — dependencias a revisar en `package.json`:**

| Dependencia | Uso esperado | Verificar |
|-------------|-------------|-----------|
| `qrcode.react` | Generación de QR | ¿Se usa en algún componente? |

### Componente 6: Verificador de Seguridad Multi-Tenant

**Checks automáticos a ejecutar:**

```python
# Check 1: Rutas sin @require_auth
# Buscar en app/rutas/ todos los endpoints que no sean /health, /docs, /auth/login
# y verificar que tengan @require_auth

# Check 2: Queries sin filtro taller_id
# Buscar en app/repositorios/ queries que accedan a tablas operativas
# sin filtrar por taller_id

# Check 3: taller_id del cliente
# Buscar en app/rutas/ y app/servicios/ uso de datos.taller_id o request.query_params["taller_id"]
# en lugar de request.state.taller_id

# Check 4: SUPER_ADMIN mezclado con roles de taller
# Buscar @require_role con combinaciones que incluyan SUPER_ADMIN junto a ADMIN/MECANICO
```

**Patrón de búsqueda con grep:**
```bash
# Endpoints sin protección
grep -rn "^@router\." app/rutas/ | grep -v "@require_auth" | grep -v "login\|health\|docs"

# taller_id del cliente (incorrecto)
grep -rn "datos\.taller_id\|body\.taller_id\|request\.query_params\[.taller_id" app/

# SUPER_ADMIN mezclado
grep -rn "@require_role" app/rutas/ | grep "SUPER_ADMIN" | grep -E "ADMIN|MECANICO"
```

---

## Data Models

### Modelo de hallazgo de auditoría

```python
@dataclass
class HallazgoAuditoria:
    tipo: str           # "codigo_duplicado" | "codigo_muerto" | "import_no_usado" | etc.
    severidad: str      # "critico" | "alto" | "medio" | "bajo"
    archivo: str        # ruta relativa al archivo
    linea: int          # número de línea (0 si aplica a todo el archivo)
    descripcion: str    # descripción del problema
    recomendacion: str  # acción a tomar
    accion: str         # "eliminar" | "consolidar" | "refactorizar" | "revisar"
```

### Estructura del reporte de auditoría

```markdown
# Reporte de Auditoría — {fecha}

## Resumen Ejecutivo
- Total archivos analizados: N
- Archivos con problemas: N
- Hallazgos críticos: N
- Hallazgos altos: N
- Hallazgos medios: N
- Hallazgos bajos: N
- Índice de calidad: N/100

## Hallazgos por Categoría
### Scripts Obsoletos (Fase 3A — Bajo Riesgo)
### Imports No Usados (Fase 3B — Riesgo Medio)
### Código Muerto (Fase 3B — Riesgo Medio)
### Código Duplicado (Fase 3C — Alto Riesgo)
### Problemas de Seguridad (Fase 3C — Crítico)
### Dependencias No Usadas (Fase 3B — Riesgo Medio)
```

---

## Implementation Plan

### Fase 0: Preparación (antes de tocar código)

1. Verificar que todos los tests pasan: `pytest tests/ -v`
2. Crear rama de limpieza: `git checkout -b limpieza-codigo-$(date +%Y%m%d)`
3. Registrar métricas baseline:
   - Total líneas de código: `find app/ -name "*.py" | xargs wc -l | tail -1`
   - Total archivos Python: `find app/ -name "*.py" | wc -l`
   - Tests pasando: `pytest --tb=no -q`

### Fase 1: Auditoría Automatizada

**Instalar herramientas de análisis:**
```bash
pip install vulture radon bandit pylint
cd frontend && npm install -D eslint depcheck
```

**Ejecutar análisis:**
```bash
# Código muerto Python
vulture app/ --min-confidence 80 > .kiro/specs/limpieza-codigo-completo/vulture-report.txt

# Complejidad ciclomática
radon cc app/ -a -s > .kiro/specs/limpieza-codigo-completo/radon-report.txt

# Seguridad
bandit -r app/ -f txt > .kiro/specs/limpieza-codigo-completo/bandit-report.txt

# Frontend
cd frontend && npx depcheck > ../.kiro/specs/limpieza-codigo-completo/depcheck-report.txt
```

### Fase 2: Auditoría Manual

Revisar manualmente:
1. `app/rutas/mobile_ruta.py` vs `app/rutas/mobile_api_ruta.py`
2. `app/servicios/whatsapp_service.py` vs `app/servicios/twilio_whatsapp_service.py`
3. `app/utils/pdf_generator.py` vs `app/utils/pdf_economia.py`
4. `app/repositorios/tenant_repository.py` — verificar uso
5. `requirements.txt` — Flask, Werkzeug, nltk, gunicorn
6. Todos los scripts con prefijo `_`
7. `frontend/src/components/` — componentes no importados

### Fase 3A: Limpieza de Bajo Riesgo (scripts obsoletos)

**Acciones:**
- Eliminar los 8 scripts con prefijo `_`
- Eliminar `scripts/apply_db_indexes.sh` y `scripts/apply_indexes_python.py` (consolidar en `create_all_indexes.py`)
- Revisar y posiblemente eliminar `scripts/crear_v3.py` si ya fue ejecutado
- Revisar `scripts/crear_super_admin_py.py` — el canónico es el `.sql`

**Verificación:** `pytest tests/ -q` debe pasar sin cambios.

### Fase 3B: Limpieza de Riesgo Medio (imports, dead code, dependencias)

**Acciones:**
- Eliminar imports no usados en todos los archivos Python (usar `autoflake`)
- Eliminar funciones muertas identificadas por `vulture` con confianza ≥ 80%
- Eliminar componentes React no usados
- Eliminar dependencias no usadas de `requirements.txt` y `package.json`
- Separar dependencias de dev de producción en `requirements.txt`

**Verificación:** `pytest tests/ -q` + `npm run test` deben pasar.

### Fase 3C: Limpieza de Alto Riesgo (duplicación, consolidación)

**Acciones:**
- Consolidar servicios de WhatsApp en uno solo con patrón Strategy
- Resolver duplicación de rutas mobile
- Extraer `verificar_pertenencia()` a `app/utils/tenant_guard.py`
- Consolidar scripts de índices de BD
- Resolver duplicación de generadores de PDF si aplica

**Verificación:** `pytest tests/ -q` + smoke test manual de endpoints críticos.

---

## Correctness Properties

Las siguientes propiedades deben mantenerse verdaderas después de cada fase de limpieza:

### Propiedad 1: Aislamiento Multi-Tenant Intacto
```python
# Para cualquier endpoint operativo, el taller_id siempre viene del JWT
# NUNCA del body, query params o headers del cliente
@given(st.integers(min_value=1), st.integers(min_value=1))
def test_taller_id_siempre_del_jwt(taller_id_jwt, taller_id_body):
    assume(taller_id_jwt != taller_id_body)
    # Un usuario del taller A nunca puede ver datos del taller B
    # aunque envíe taller_id=B en el body
    assert datos_retornados.taller_id == taller_id_jwt
```

### Propiedad 2: Todos los Endpoints Protegidos
```python
# Para todo endpoint que no sea público, debe existir @require_auth
# Esta propiedad se verifica con análisis estático del AST
def test_endpoints_tienen_require_auth():
    for ruta_file in glob("app/rutas/*.py"):
        endpoints = extraer_endpoints(ruta_file)
        for endpoint in endpoints:
            if not es_publico(endpoint):
                assert tiene_require_auth(endpoint), f"{endpoint} sin @require_auth"
```

### Propiedad 3: Tests Pasan Después de Cada Cambio
```python
# Invariante: pytest debe retornar exit code 0 después de cada commit de limpieza
# Se verifica ejecutando pytest antes de cada git commit en la rama de limpieza
```

### Propiedad 4: Sin Regresión de Funcionalidad
```python
# Los endpoints críticos deben responder igual antes y después de la limpieza
# POST /auth/login → 200 con credenciales válidas
# GET /health → 200
# POST /tickets → 201 con datos válidos y JWT válido
```

### Propiedad 5: Dependencias de Producción No Contienen Dev Tools
```python
# requirements.txt de producción no debe contener: pytest, mypy, pre-commit, safety, bandit
def test_no_dev_deps_en_produccion():
    dev_only = {"pytest", "mypy", "pre-commit", "safety", "bandit", "ruff", "pylint"}
    prod_deps = leer_requirements("requirements.txt")
    assert not dev_only.intersection(prod_deps), "Dev deps en producción"
```

---

## Files to Create / Modify

### Archivos nuevos a crear

| Archivo | Propósito |
|---------|-----------|
| `app/utils/tenant_guard.py` | Helper centralizado para verificar pertenencia al taller |
| `scripts/run_auditoria.sh` | Script ejecutable de auditoría completa |
| `.auditoria-ignore` | Exclusiones configurables para la auditoría |
| `requirements-dev.txt` | Dependencias solo de desarrollo separadas |
| `.kiro/specs/limpieza-codigo-completo/auditoria-report.md` | Reporte generado |
| `.kiro/specs/limpieza-codigo-completo/plan-limpieza.md` | Plan de limpieza priorizado |
| `CHANGELOG-LIMPIEZA.md` | Registro de todos los cambios realizados |

### Archivos a eliminar (Fase 3A — confirmados)

| Archivo | Razón |
|---------|-------|
| `scripts/_aplicar_columnas_faltantes.py` | Script de fix puntual ya ejecutado |
| `scripts/_check_audit.py` | Script de verificación temporal |
| `scripts/_check_db.py` | Duplicado de `scripts/check_db.py` |
| `scripts/_check_login.py` | Script de debug temporal |
| `scripts/_check_which_db.py` | Script de diagnóstico temporal |
| `scripts/_test_auth_full.py` | Test manual fuera del suite |
| `scripts/_test_auth_runtime.py` | Test manual fuera del suite |
| `scripts/_test_login.py` | Duplicado de `_check_login.py` |
| `scripts/apply_db_indexes.sh` | Consolidado en `create_all_indexes.py` |
| `scripts/apply_indexes_python.py` | Consolidado en `create_all_indexes.py` |

### Archivos a modificar

| Archivo | Cambio |
|---------|--------|
| `requirements.txt` | Separar deps de dev, eliminar Flask/Werkzeug si no se usan |
| `app/servicios/whatsapp_service.py` | Consolidar con twilio_whatsapp_service.py |
| `app/utils/` | Agregar `tenant_guard.py` |
| `scripts/README.md` | Actualizar documentación de scripts |

### Archivos a revisar antes de decidir

| Archivo | Pregunta |
|---------|----------|
| `app/rutas/mobile_ruta.py` | ¿Está registrado en `main.py`? |
| `app/rutas/mobile_api_ruta.py` | ¿Está registrado en `main.py`? |
| `app/servicios/twilio_whatsapp_service.py` | ¿Cuál provider está activo? |
| `app/repositorios/tenant_repository.py` | ¿Se importa en algún servicio? |
| `scripts/crear_super_admin_py.py` | ¿Sigue siendo necesario junto al .sql? |
| `scripts/crear_v3.py` | ¿Ya fue ejecutado? ¿Es idempotente? |
| `scripts/seed_admin.py` | ¿Difiere de `seed_demo.py`? |
| `frontend/src/components/Starfield.jsx` | ¿Se importa en alguna página? |
| `frontend/src/components/PageHero.jsx` | ¿Se importa en alguna página? |
| `frontend/src/pages/InfoPage.jsx` | ¿Tiene ruta en `App.jsx`? |
