# Tareas Periódicas (Cron Jobs)

Este documento describe las tareas periódicas que deben configurarse para el mantenimiento del sistema.

## Scripts Disponibles

### 1. Limpieza de Tokens Blacklisted (`cleanup_blacklist.py`)

**Propósito**: Elimina tokens blacklisted que ya expiraron de la base de datos.

**Frecuencia recomendada**: Diario a las 2 AM

**Comando**:
```bash
python scripts/cleanup_blacklist.py
```

**Configuración cron**:
```cron
0 2 * * * cd /ruta/a/taller_api && /ruta/a/venv/bin/python scripts/cleanup_blacklist.py >> /var/log/taller_api/cleanup_blacklist.log 2>&1
```

### 2. Archival de Logs de Auditoría (`archive_audit_logs.py`)

**Propósito**: Archiva logs de auditoría antiguos a archivos JSON y opcionalmente los elimina de la BD.

**Frecuencia recomendada**: Mensual (primer día del mes a las 3 AM)

**Comando**:
```bash
# Solo archivar (mantener en BD)
python scripts/archive_audit_logs.py

# Archivar y eliminar de BD
python scripts/archive_audit_logs.py --delete

# Especificar días de retención personalizados
python scripts/archive_audit_logs.py --retention-days 60 --delete
```

**Configuración cron**:
```cron
# Archivar sin eliminar
0 3 1 * * cd /ruta/a/taller_api && /ruta/a/venv/bin/python scripts/archive_audit_logs.py >> /var/log/taller_api/archive_audit_logs.log 2>&1

# Archivar y eliminar
0 3 1 * * cd /ruta/a/taller_api && /ruta/a/venv/bin/python scripts/archive_audit_logs.py --delete >> /var/log/taller_api/archive_audit_logs.log 2>&1
```

**Nota**: Los archivos archivados se guardan en el directorio `audit_archives/`.

### 3. Reporte de Métricas de Seguridad (`security_report.py`)

**Propósito**: Genera un reporte semanal con métricas de seguridad.

**Frecuencia recomendada**: Semanal (lunes a las 8 AM)

**Comando**:
```bash
# Reporte de últimos 7 días (stdout)
python scripts/security_report.py

# Reporte de últimos 30 días guardado en archivo
python scripts/security_report.py --days 30 --output security_report_$(date +%Y%m%d).txt

# Reporte personalizado
python scripts/security_report.py --days 14 --output /var/reports/security_report.txt
```

**Configuración cron**:
```cron
# Reporte semanal guardado en archivo
0 8 * * 1 cd /ruta/a/taller_api && /ruta/a/venv/bin/python scripts/security_report.py --output /var/reports/security_report_$(date +\%Y\%m\%d).txt 2>&1

# Reporte semanal enviado por email (requiere configurar mail)
0 8 * * 1 cd /ruta/a/taller_api && /ruta/a/venv/bin/python scripts/security_report.py | mail -s "Reporte de Seguridad Semanal" admin@taller.com
```

## Configuración Completa de Crontab

Para configurar todas las tareas periódicas, edita el crontab:

```bash
crontab -e
```

Agrega las siguientes líneas (ajusta las rutas según tu instalación):

```cron
# Taller API - Tareas Periódicas

# Limpieza de tokens blacklisted (diario a las 2 AM)
0 2 * * * cd /ruta/a/taller_api && /ruta/a/venv/bin/python scripts/cleanup_blacklist.py >> /var/log/taller_api/cleanup_blacklist.log 2>&1

# Archival de audit logs (mensual, primer día a las 3 AM)
0 3 1 * * cd /ruta/a/taller_api && /ruta/a/venv/bin/python scripts/archive_audit_logs.py --delete >> /var/log/taller_api/archive_audit_logs.log 2>&1

# Reporte de seguridad (semanal, lunes a las 8 AM)
0 8 * * 1 cd /ruta/a/taller_api && /ruta/a/venv/bin/python scripts/security_report.py --output /var/reports/security_report_$(date +\%Y\%m\%d).txt 2>&1
```

## Verificación de Configuración

Para verificar que las tareas están configuradas correctamente:

```bash
# Listar tareas cron actuales
crontab -l

# Ver logs de ejecución
tail -f /var/log/taller_api/cleanup_blacklist.log
tail -f /var/log/taller_api/archive_audit_logs.log
```

## Crear Directorios de Logs

Antes de configurar las tareas, crea los directorios necesarios:

```bash
# Crear directorio de logs
sudo mkdir -p /var/log/taller_api
sudo chown $USER:$USER /var/log/taller_api

# Crear directorio de reportes
sudo mkdir -p /var/reports
sudo chown $USER:$USER /var/reports
```

## Rotación de Logs

Para evitar que los logs crezcan indefinidamente, configura logrotate:

Crea el archivo `/etc/logrotate.d/taller_api`:

```
/var/log/taller_api/*.log {
    daily
    rotate 30
    compress
    delaycompress
    notifempty
    missingok
    create 0644 usuario usuario
}
```

## Monitoreo de Tareas

Para monitorear que las tareas se ejecutan correctamente:

1. **Revisar logs regularmente**:
   ```bash
   ls -lh /var/log/taller_api/
   ```

2. **Verificar archivos archivados**:
   ```bash
   ls -lh audit_archives/
   ```

3. **Revisar reportes de seguridad**:
   ```bash
   ls -lh /var/reports/
   ```

4. **Configurar alertas** (opcional):
   - Usar herramientas como `monit` o `supervisor` para monitorear ejecución
   - Configurar notificaciones por email en caso de fallos

## Troubleshooting

### Las tareas no se ejecutan

1. Verificar que cron está corriendo:
   ```bash
   sudo systemctl status cron
   ```

2. Verificar permisos de los scripts:
   ```bash
   chmod +x scripts/*.py
   ```

3. Verificar que el entorno virtual está activado en cron:
   ```bash
   # Usar ruta completa al python del venv
   /ruta/a/venv/bin/python scripts/cleanup_blacklist.py
   ```

### Errores de base de datos

1. Verificar que las variables de entorno están disponibles:
   ```bash
   # Agregar al inicio del script cron
   source /ruta/a/taller_api/.env
   ```

2. Verificar conexión a base de datos:
   ```bash
   psql -U postgres -d taller_db -c "SELECT 1;"
   ```

### Logs no se generan

1. Verificar permisos del directorio de logs:
   ```bash
   ls -ld /var/log/taller_api/
   ```

2. Crear directorio si no existe:
   ```bash
   mkdir -p /var/log/taller_api
   ```

## Recomendaciones

1. **Backup antes de eliminar**: Siempre haz backup de la base de datos antes de ejecutar scripts que eliminan datos.

2. **Probar manualmente primero**: Ejecuta cada script manualmente antes de configurarlo en cron para verificar que funciona correctamente.

3. **Monitorear espacio en disco**: Los archivos archivados pueden crecer. Configura limpieza automática o compresión.

4. **Revisar reportes regularmente**: Los reportes de seguridad son útiles solo si se revisan. Configura alertas para anomalías.

5. **Ajustar frecuencias**: Las frecuencias recomendadas son un punto de partida. Ajústalas según las necesidades de tu sistema.
