# Scripts de Migración

Este directorio contiene scripts de migración y mantenimiento para el sistema.

## migrate_passwords.py

Script de migración de contraseñas desde `configuracion_seguridad` a la nueva tabla `users` con sistema JWT.

### Descripción

Este script migra las contraseñas SHA256 existentes en la tabla `configuracion_seguridad` a la nueva tabla `users`. Las contraseñas se copian directamente (sin re-hashear) y se marcan con `is_migrated=False` para que en el próximo login se conviertan automáticamente a bcrypt.

### Requisitos Previos

1. Base de datos debe tener las siguientes tablas:
   - `users`
   - `roles`
   - `user_roles`
   - `audit_log`
   - `configuracion_seguridad`

2. Debe existir el rol `ADMIN` en la tabla `roles`

3. Variable de entorno `DATABASE_URL` configurada (o usar default)

### Uso

```bash
python scripts/migrate_passwords.py
```

El script solicitará confirmación antes de ejecutar la migración.

### Proceso de Migración

1. Lee todos los registros de `configuracion_seguridad`
2. Para cada registro:
   - Genera username basado en la clave (ej: `economia_password` → `economia`)
   - Crea usuario en tabla `users` con hash SHA256 temporal
   - Marca `is_migrated=False`
   - Asigna rol `ADMIN` por defecto
   - Registra migración en `audit_log` con action `PASSWORD_MIGRATED`
3. Genera reporte detallado de la migración
4. Guarda reporte en archivo `migration_report_YYYYMMDD_HHMMSS.txt`

### Comportamiento

- **Usuarios existentes**: Si un usuario ya existe, se omite la migración
- **Emails duplicados**: Si el email ya existe, se agrega timestamp para hacerlo único
- **Sin rol ADMIN**: El script falla si no existe el rol ADMIN en la base de datos
- **Tabla vacía**: Si no hay registros en `configuracion_seguridad`, el script completa sin errores

### Reporte de Migración

El script genera un reporte detallado que incluye:

- Total de registros procesados
- Número de migraciones exitosas
- Número de migraciones fallidas
- Número de migraciones omitidas
- Lista de usuarios creados
- Lista de errores (si los hubo)
- Duración de la migración

El reporte se imprime en consola y se guarda en un archivo.

### Ejemplo de Salida

```
======================================================================
REPORTE DE MIGRACIÓN DE CONTRASEÑAS
======================================================================

Fecha: 2026-03-28 10:30:45
Duración: 2.34 segundos

Total procesados: 3
Exitosos: 3
Fallidos: 0
Omitidos: 0

──────────────────────────────────────────────────────────────────────
USUARIOS CREADOS:
──────────────────────────────────────────────────────────────────────
  ✓ economia (origen: economia_password)
  ✓ admin (origen: admin_password)
  ✓ mecanico (origen: mecanico_password)

======================================================================
```

### Auditoría

Cada migración se registra en `audit_log` con:

- `action`: `PASSWORD_MIGRATED`
- `resource_type`: `user`
- `resource_id`: ID del usuario creado
- `ip_address`: `127.0.0.1` (script local)
- `user_agent`: `migration_script`
- `details`: JSON con información de la migración

### Validación

El script incluye tests unitarios en `tests/test_migrate_passwords.py` que validan:

- Generación correcta de usernames
- Migración exitosa de contraseñas
- Omisión de usuarios existentes
- Manejo de errores (rol ADMIN faltante)
- Manejo de tabla vacía
- Funcionalidad del reporte

Para ejecutar los tests:

```bash
python -m pytest tests/test_migrate_passwords.py -v
```

### Notas Importantes

- Las contraseñas se copian directamente sin re-hashear
- Los usuarios migrados tendrán `is_migrated=False`
- En el próximo login, las contraseñas se convertirán automáticamente a bcrypt
- Todos los usuarios migrados reciben rol `ADMIN` por defecto
- El script es idempotente: puede ejecutarse múltiples veces sin duplicar usuarios
