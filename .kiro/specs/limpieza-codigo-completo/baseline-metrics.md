# Métricas Baseline — Limpieza de Código Completo

Fecha: 2026-04-24 23:10:04

## Tests Baseline

- Comando: `pytest tests/ -q --tb=no`
- Tests pasando: 364
- Tests fallando: 151
- Tests con error: 28 (errores en ejecución) + 3 (errores de colección — import errors pre-existentes)
- Tests omitidos: 11
- Total colectados: 554 (de los cuales 3 archivos no pudieron colectarse por import errors)
- Salida completa: ver `.kiro_tmp/baseline_tests.txt`

## Notas sobre los errores de colección

Los 3 archivos con errores de colección tienen import errors pre-existentes (no relacionados con la limpieza):

| Archivo | Error |
|---------|-------|
| `tests/test_error_messages.py` | `ImportError: cannot import name 'UserRole' from 'app.modelos.role'` |
| `tests/test_migrate_passwords.py` | `ImportError: cannot import name 'AuditLog' from 'app.modelos'` |
| `tests/test_role_permissions.py` | `ImportError: cannot import name 'UserRole' from 'app.modelos.role'` |

Estos 3 archivos fueron excluidos de la ejecución del baseline. Los números de arriba corresponden a los 551 tests colectables.

## Resumen de tests fallando por categoría

Los 151 tests fallando y 28 errores en ejecución son pre-existentes al inicio de la limpieza. Las categorías principales:

- **Integración BD** (`tests/integration/`): 11 fallos (migraciones, PDF, compresión)
- **Auth service/ruta** (`test_auth_*.py`): ~20 fallos
- **Preservación** (`test_preservation*.py`): ~20 fallos
- **Bug condition tests** (`test_bug_*.py`): ~25 fallos (tests que documentan bugs conocidos)
- **Tenant isolation** (`test_tenant_isolation.py`, `test_super_admin_isolation.py`): ~10 fallos
- **WhatsApp** (`test_whatsapp_*.py`): ~10 fallos
- **Users ruta** (`test_users_ruta.py`): 22 errores en ejecución
- **Endpoint protection** (`test_endpoint_protection.py`): 6 errores en ejecución
- **Otros** (`test_user_service.py`, `test_token_manager_properties.py`, etc.): resto

## Objetivo de la limpieza

Al finalizar todas las fases de limpieza, el número de tests pasando debe ser **≥ 364** y los tests fallando deben ser **≤ 151**. Cualquier regresión introducida por la limpieza debe detectarse comparando contra este baseline.

## Métricas de Código Baseline

Fecha de medición: 2026-04-24

### Backend (app/)
- Archivos Python: 105
- Líneas brutas (incluyendo blancos y comentarios): 14.846
- Líneas de código efectivas (sin blancos ni comentarios): 14.244

### Tests (tests/)
- Archivos Python: 60
- Líneas brutas: 15.837

### Scripts (scripts/)
- Archivos Python: 25
- Líneas brutas: 1.856

### Frontend (frontend/src/)
- Archivos JS/JSX: 29
- Líneas brutas: 7.511

### Total general
- Total archivos Python (app/ + tests/ + scripts/): 190
- Total líneas brutas Python (app/ + tests/ + scripts/): 32.539
- Total archivos JS/JSX: 29

## Herramientas de Análisis Estático Instaladas

| Herramienta | Versión | Propósito |
|-------------|---------|-----------|
| vulture | 2.16 | Detección de código muerto |
| radon | 6.0.1 | Complejidad ciclomática |
| bandit | 1.9.4 | Análisis de seguridad |
