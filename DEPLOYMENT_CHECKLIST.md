# Checklist de Deployment - Sistema JWT

## Pre-Deployment

### 1. Configuración de Variables de Entorno

- [ ] Configurar JWT_SECRET_KEY (mínimo 32 caracteres, usar `openssl rand -hex 32`)
- [ ] Configurar JWT_ALGORITHM=HS256
- [ ] Configurar JWT_ACCESS_TOKEN_EXPIRE_MINUTES=15
- [ ] Configurar JWT_REFRESH_TOKEN_EXPIRE_DAYS=7
- [ ] Configurar BCRYPT_COST_FACTOR=12
- [ ] Configurar PASSWORD_MIN_LENGTH=8
- [ ] Configurar RATE_LIMIT_* variables
- [ ] Configurar SMTP_* variables para password reset
- [ ] Configurar ENVIRONMENT=production
- [ ] Configurar ENABLE_LEGACY_AUTH=true (para período de transición)
- [ ] Configurar ALLOWED_ORIGINS con dominios específicos (no usar *)

### 2. Base de Datos

- [ ] Hacer backup completo de la base de datos
- [ ] Ejecutar migración SQL: `sqlite3 taller.db < db/migracion_jwt_auth_2026_03_28.sql`
- [ ] Verificar que todas las tablas fueron creadas correctamente
- [ ] Verificar que los roles por defecto fueron insertados

### 3. Migración de Contraseñas

- [ ] Ejecutar script de migración: `python scripts/migrate_passwords.py`
- [ ] Verificar el reporte de migración
- [ ] Confirmar que todos los usuarios fueron migrados

### 4. Tests y Validación

- [ ] Ejecutar todos los tests: `pytest`
- [ ] Verificar cobertura de tests: `pytest --cov=app`
- [ ] Ejecutar análisis de seguridad: `bandit -r app/ -c .bandit`
- [ ] Verificar dependencias: `safety check`
- [ ] Actualizar dependencias vulnerables si es necesario

### 5. Documentación

- [ ] Revisar docs/MIGRACION_JWT.md
- [ ] Actualizar README.md con nuevas variables de entorno
- [ ] Documentar proceso de rollback
- [ ] Notificar a usuarios sobre cambios en la API

## Deployment Steps

### 1. Backup

```bash
# Backup de base de datos
cp taller.db taller.db.backup.$(date +%Y%m%d_%H%M%S)

# Backup de código
git tag pre-jwt-migration-$(date +%Y%m%d)
```

### 2. Deploy Backend

```bash
# Ejecutar script de deployment
bash scripts/deploy.sh
```

El script deploy.sh hace:
- Backup de base de datos
- Ejecuta migración SQL
- Ejecuta migración de contraseñas
- Reinicia el servidor
- Verifica health check

### 3. Deploy Clientes

#### App Móvil
- [ ] Actualizar app móvil con nueva versión que usa JWT
- [ ] Publicar en stores (App Store, Google Play)
- [ ] Notificar a usuarios para actualizar

#### Frontend Web
- [ ] Deploy de frontend web con autenticación JWT
- [ ] Verificar que axios está configurado correctamente
- [ ] Probar login en producción

## Post-Deployment Verification

### 1. Verificación Funcional

- [ ] Probar login con usuario existente
- [ ] Verificar que access token funciona
- [ ] Probar refresh token
- [ ] Probar logout
- [ ] Verificar que endpoints protegidos requieren autenticación
- [ ] Probar password reset flow completo

### 2. Verificación de Auditoría

- [ ] Verificar que eventos se registran en audit_log
- [ ] Consultar endpoint GET /audit-log
- [ ] Verificar que failed login attempts se registran con IP

### 3. Verificación de Rate Limiting

- [ ] Hacer múltiples requests a /auth/login
- [ ] Verificar que retorna 429 después del límite
- [ ] Verificar header Retry-After en respuesta 429

### 4. Verificación de Modo Offline (App Móvil)

- [ ] Desconectar internet en dispositivo móvil
- [ ] Crear operaciones offline
- [ ] Reconectar internet
- [ ] Verificar que operaciones se sincronizan automáticamente

### 5. Monitoreo

- [ ] Verificar que logs se están generando correctamente
- [ ] Configurar alertas de seguridad
- [ ] Verificar métricas de aplicación
- [ ] Monitorear errores en primeras 24 horas

## Rollback Plan

Si algo sale mal durante el deployment:

```bash
# Ejecutar script de rollback
bash scripts/rollback.sh
```

El script rollback.sh hace:
- Revierte código a versión anterior
- Habilita modo legacy (ENABLE_LEGACY_AUTH=true)
- Revierte base de datos si es necesario
- Reinicia el servidor

### Rollback Manual

Si el script falla:

1. **Revertir código**:
   ```bash
   git checkout pre-jwt-migration-YYYYMMDD
   ```

2. **Revertir base de datos**:
   ```bash
   cp taller.db.backup.YYYYMMDD_HHMMSS taller.db
   ```

3. **Habilitar modo legacy**:
   ```bash
   echo "ENABLE_LEGACY_AUTH=true" >> .env
   ```

4. **Reiniciar servidor**:
   ```bash
   systemctl restart taller-api
   ```

## Período de Transición

Durante los primeros 30 días:
- Mantener ENABLE_LEGACY_AUTH=true
- Usuarios con contraseñas SHA256 pueden hacer login
- Contraseñas se migran automáticamente a bcrypt en primer login
- Monitorear logs de migración automática

Después de 30 días:
- Verificar que todos los usuarios activos migraron
- Deshabilitar modo legacy: ENABLE_LEGACY_AUTH=false
- Eliminar código de compatibilidad SHA256 (opcional)

## Contactos de Emergencia

- Desarrollador: [NOMBRE]
- DevOps: [NOMBRE]
- Soporte: [EMAIL/TELÉFONO]

## Notas Adicionales

- El sistema soporta rollback completo en cualquier momento
- Los tokens JWT expiran automáticamente (15 min access, 7 días refresh)
- La blacklist de tokens se limpia automáticamente con cron job diario
- Los audit logs se archivan mensualmente con cron job
