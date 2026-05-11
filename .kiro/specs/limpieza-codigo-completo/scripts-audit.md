# Auditoría de Scripts — Fase 1

Generado durante la ejecución de la Tarea 4.

---

## 4.1 Scripts documentados como necesarios

### Documentados en `scripts/README.md`
Solo documenta **un script**:
- `scripts/migrate_passwords.py` — migración de contraseñas SHA256 → bcrypt. Script de migración puntual con tests en `tests/test_migrate_passwords.py`. **Idempotente.**

### Documentados en `scripts/CRON_JOBS.md`
Tres scripts de cron jobs activos:
- `scripts/cleanup_blacklist.py` — limpieza diaria de tokens blacklisted expirados
- `scripts/archive_audit_logs.py` — archival mensual de logs de auditoría
- `scripts/security_report.py` — reporte semanal de métricas de seguridad

### Scripts necesarios adicionales (inferidos por uso en Docker/deploy)
- `scripts/entrypoint.sh` — usado por Docker como entrypoint
- `scripts/deploy.sh` — despliegue
- `scripts/rollback.sh` — rollback de despliegue
- `scripts/init_database.py` — inicialización de BD
- `scripts/crear_super_admin.sql` — canónico para crear SUPER_ADMIN (ver steering)
- `scripts/generar_hash_bcrypt.py` — auxiliar requerido por `crear_super_admin.sql`
- `scripts/seed_demo.py` — seed de datos de demo (ver 4.2)
- `scripts/create_all_indexes.py` — canónico de índices (ver 4.5)
- `scripts/verificar_migracion.py` — verificación de migraciones
- `scripts/run_sql_migration.py` — ejecución de migraciones SQL
- `scripts/check_db.py` — verificación de BD (sin prefijo `_`, no temporal)
- `scripts/check_indexes.py` — verificación de índices
- `scripts/check_security_alerts.py` — verificación de alertas de seguridad
- `scripts/update_dependencies.sh` — actualización de dependencias
- `scripts/fix-frontend-urls.sh` — corrección de URLs del frontend

---

## 4.2 seed_admin.py vs seed_demo.py

### Diferencias

| Aspecto | `seed_admin.py` | `seed_demo.py` |
|---------|----------------|----------------|
| **Propósito** | Crea un usuario `admin` genérico sin taller | Crea un taller completo con admin + mecánico + datos de demo |
| **Taller** | No crea taller (usuario sin `taller_id`) | Crea taller "Taller Demo Notificaciones" |
| **Usuarios** | 1 usuario `admin` con rol ADMIN | 2 usuarios: `admin_demo` + `mecanico_demo` |
| **Datos** | Solo usuario + roles | Taller + usuarios + mecánico + vehículo + tickets + notificaciones |
| **Idempotente** | Sí (verifica si ya existe) | Sí (limpia datos previos antes de crear) |
| **Credenciales** | Configurable por env vars | Hardcodeadas: `Demo1234!` |
| **Uso previsto** | Inicialización de entorno vacío | Demo/desarrollo del sistema de notificaciones |

### Problema crítico en `seed_admin.py`
Crea un usuario `admin` **sin `taller_id`** (NULL), lo que viola la arquitectura multi-tenant. Un usuario sin taller no puede operar en el sistema. Este script es un remanente de antes de que se implementara el modelo multi-tenant completo.

### Veredicto
**`seed_admin.py` es OBSOLETO y debe eliminarse.** Razones:
1. Crea un usuario sin `taller_id`, incompatible con la arquitectura multi-tenant actual
2. `seed_demo.py` cubre el caso de uso de inicialización con datos de prueba de forma más completa
3. Para crear el primer admin de un taller real, el flujo correcto es: crear taller vía SUPER_ADMIN → crear usuario vía endpoint de la API
4. No está documentado en `README.md` ni en `CRON_JOBS.md`

---

## 4.3 crear_super_admin_py.py vs crear_super_admin.sql

### Análisis

Ambos scripts hacen exactamente lo mismo: crear el usuario `superadmin` con rol `SUPER_ADMIN` y `taller_id = NULL`.

| Aspecto | `crear_super_admin_py.py` | `crear_super_admin.sql` |
|---------|--------------------------|------------------------|
| **Tecnología** | Python + SQLAlchemy | SQL puro (psql) |
| **Credenciales hardcodeadas** | ⚠️ **SÍ** — `DB_URL` con usuario/contraseña en el código | No — usa psql con credenciales del entorno |
| **Contraseña hardcodeada** | ⚠️ **SÍ** — `SuperAdmin2026!` en texto plano | No — requiere hash generado por `generar_hash_bcrypt.py` |
| **Validaciones** | Ninguna | Verifica que las tablas existen antes de ejecutar |
| **Documentación** | Mínima (docstring de 3 líneas) | Extensa con advertencias de seguridad |
| **Idempotente** | Sí | Sí |
| **Seguridad** | ❌ Credenciales hardcodeadas | ✅ Proceso seguro con hash externo |

### Veredicto
**`crear_super_admin_py.py` es OBSOLETO y debe eliminarse.** Razones:
1. Tiene credenciales de BD hardcodeadas (`postgres:123456@localhost`) — violación de seguridad
2. Tiene contraseña del SUPER_ADMIN hardcodeada en texto plano — violación crítica de seguridad
3. El steering del proyecto establece explícitamente que `crear_super_admin.sql` es el canónico
4. `crear_super_admin.sql` tiene mejor seguridad, validaciones y documentación

---

## 4.4 crear_v3.py — ¿Script de migración ya ejecutado?

### Análisis

`crear_v3.py` hace tres cosas:
1. Crea la base de datos `taller_v3` si no existe
2. Ejecuta `db/setup_v3_completo.sql` (que existe en el repo)
3. Verifica las tablas, versiones de Alembic, talleres y roles creados

### Indicadores de que ya fue ejecutado
- El nombre `crear_v3.py` sugiere que fue el script de inicialización de la versión 3 del sistema
- El proyecto ya tiene migraciones Alembic activas (`alembic/versions/`) que gestionan el esquema
- Tiene credenciales hardcodeadas (`postgres:123456`) — patrón de script de setup inicial
- Referencia a `LC_COLLATE 'Spanish_Colombia.1252'` — configuración específica de entorno de desarrollo Windows
- El sistema ya está en producción con la BD `taller_v3` creada

### Problema
El script tiene **credenciales hardcodeadas** y una configuración de collation específica de Windows (`Spanish_Colombia.1252`) que fallaría en Linux/Docker.

### Veredicto
**`crear_v3.py` es OBSOLETO y debe eliminarse.** Razones:
1. Es un script de setup inicial de la BD que ya fue ejecutado — el sistema ya tiene la BD `taller_v3`
2. Las migraciones Alembic (`alembic upgrade head`) son el mecanismo correcto para gestionar el esquema
3. Tiene credenciales hardcodeadas — violación de seguridad
4. La configuración de collation `Spanish_Colombia.1252` es específica de Windows y fallaría en producción Linux
5. `db/setup_v3_completo.sql` existe pero es un artefacto del setup inicial, no del flujo de migraciones actual

---

## 4.5 Tres scripts de índices: apply_db_indexes.sh vs apply_indexes_python.py vs create_all_indexes.py

### Comparación

| Aspecto | `apply_db_indexes.sh` | `apply_indexes_python.py` | `create_all_indexes.py` |
|---------|----------------------|--------------------------|------------------------|
| **Tecnología** | Bash + psql | Python + SQLAlchemy | Python + SQLAlchemy |
| **Índices definidos** | Delega a `db/migrations/add_composite_indexes.sql` | Delega a `db/migrations/add_composite_indexes.sql` | Define 5 índices inline en el código |
| **Portabilidad** | ❌ Requiere psql instalado | ✅ Solo Python | ✅ Solo Python |
| **Idempotente** | Depende del SQL | Depende del SQL | ✅ Usa `CREATE INDEX IF NOT EXISTS` |
| **Manejo de errores** | `set -e` básico | Try/except por statement | Try/except por índice |
| **Credenciales** | Variables de entorno | Variables de entorno (con fallback hardcodeado) | Variables de entorno (con fallback hardcodeado) |
| **Granularidad** | Todo o nada | Todo o nada | Índice por índice |

### Índices en `create_all_indexes.py`
```
idx_tickets_estado_fecha     → tickets(estado, fecha_ingreso DESC)
idx_tickets_placa            → tickets(placa)
idx_audit_log_user_action_date → audit_log(user_id, action, timestamp DESC)
idx_token_blacklist_jti_exp  → token_blacklist(jti, expires_at)
idx_vehiculos_placa          → vehiculos(placa)
```

### Nota sobre `add_composite_indexes.sql`
El archivo `db/migrations/add_composite_indexes.sql` existe y es referenciado por los dos scripts obsoletos. Sus índices pueden diferir de los de `create_all_indexes.py` — esto debe verificarse antes de eliminar los scripts.

### Veredicto
**`apply_db_indexes.sh` y `apply_indexes_python.py` son OBSOLETOS y deben eliminarse.** `create_all_indexes.py` es el canónico. Razones:
1. `create_all_indexes.py` es más portable (solo Python, sin dependencia de psql)
2. `create_all_indexes.py` es idempotente por diseño (`IF NOT EXISTS`)
3. `create_all_indexes.py` tiene mejor manejo de errores (continúa si un índice falla)
4. Los dos scripts obsoletos dependen de un archivo SQL externo que puede estar desactualizado
5. El diseño del spec ya establece `create_all_indexes.py` como el canónico

**Acción adicional recomendada:** Antes de eliminar los scripts, verificar que los índices en `db/migrations/add_composite_indexes.sql` estén todos cubiertos en `create_all_indexes.py`. Si hay índices adicionales en el SQL, agregarlos a `create_all_indexes.py`.

---

## Resumen de Hallazgos — Scripts

### Scripts a eliminar (confirmados)

| Script | Razón | Severidad |
|--------|-------|-----------|
| `scripts/seed_admin.py` | Crea usuario sin taller_id, incompatible con multi-tenant | Alto |
| `scripts/crear_super_admin_py.py` | Credenciales hardcodeadas, reemplazado por .sql canónico | **Crítico** |
| `scripts/crear_v3.py` | Setup inicial ya ejecutado, credenciales hardcodeadas | **Crítico** |
| `scripts/apply_db_indexes.sh` | Consolidado en create_all_indexes.py | Bajo |
| `scripts/apply_indexes_python.py` | Consolidado en create_all_indexes.py | Bajo |
| `scripts/_aplicar_columnas_faltantes.py` | Script de fix puntual (prefijo `_`) | Bajo |
| `scripts/_check_audit.py` | Script temporal de verificación (prefijo `_`) | Bajo |
| `scripts/_check_db.py` | Duplicado de check_db.py (prefijo `_`) | Bajo |
| `scripts/_check_login.py` | Script de debug temporal (prefijo `_`) | Bajo |
| `scripts/_check_which_db.py` | Script de diagnóstico temporal (prefijo `_`) | Bajo |
| `scripts/_test_auth_full.py` | Test manual fuera del suite (prefijo `_`) | Bajo |
| `scripts/_test_auth_runtime.py` | Test manual fuera del suite (prefijo `_`) | Bajo |
| `scripts/_test_login.py` | Duplicado de _check_login.py (prefijo `_`) | Bajo |

**Total: 13 scripts a eliminar** (8 con prefijo `_` ya identificados en Fase 3A + 5 adicionales)

### Scripts a mantener

| Script | Razón |
|--------|-------|
| `scripts/cleanup_blacklist.py` | Cron job documentado |
| `scripts/archive_audit_logs.py` | Cron job documentado |
| `scripts/security_report.py` | Cron job documentado |
| `scripts/migrate_passwords.py` | Documentado en README, tiene tests |
| `scripts/crear_super_admin.sql` | Canónico para SUPER_ADMIN (steering) |
| `scripts/generar_hash_bcrypt.py` | Auxiliar requerido por crear_super_admin.sql |
| `scripts/seed_demo.py` | Seed de datos de demo |
| `scripts/create_all_indexes.py` | Canónico de índices |
| `scripts/init_database.py` | Inicialización de BD |
| `scripts/entrypoint.sh` | Usado por Docker |
| `scripts/deploy.sh` | Despliegue |
| `scripts/rollback.sh` | Rollback |
| `scripts/verificar_migracion.py` | Verificación de migraciones |
| `scripts/run_sql_migration.py` | Ejecución de migraciones SQL |
| `scripts/check_db.py` | Verificación de BD |
| `scripts/check_indexes.py` | Verificación de índices |
| `scripts/check_security_alerts.py` | Verificación de alertas |
| `scripts/update_dependencies.sh` | Actualización de dependencias |
| `scripts/fix-frontend-urls.sh` | Corrección de URLs |

### Acción adicional recomendada
- Actualizar `scripts/README.md` para documentar todos los scripts que se mantienen (actualmente solo documenta `migrate_passwords.py`)
- Verificar que los índices de `db/migrations/add_composite_indexes.sql` estén cubiertos en `create_all_indexes.py` antes de eliminar los scripts de índices obsoletos
