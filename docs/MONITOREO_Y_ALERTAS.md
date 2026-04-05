# Monitoreo y Alertas - Taller API

Esta guía describe cómo configurar monitoreo y alertas para el sistema de Taller API.

## Logging de Errores

### Configuración de Logs

El sistema registra logs en diferentes niveles:

- **INFO**: Eventos normales (login exitoso, operaciones completadas)
- **WARNING**: Situaciones anómalas pero no críticas (rate limiting, intentos fallidos)
- **ERROR**: Errores que requieren atención (excepciones, fallos de BD)
- **CRITICAL**: Errores críticos del sistema

### Logs de Aplicación

**Desarrollo**:
```bash
uvicorn app.main:app --reload --log-level info
```

**Producción con Gunicorn**:
```bash
gunicorn app.main:app \
  -w 4 \
  -k uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --access-logfile /var/log/taller_api/access.log \
  --error-logfile /var/log/taller_api/error.log \
  --log-level warning
```

### Estructura de Logs de Error

Todos los errores se registran con el siguiente formato:

```
[ERROR {error_id}] {exception_type}: {message}
Context: {
  "error_id": "uuid",
  "path": "/api/endpoint",
  "method": "POST",
  "client_ip": "192.168.1.100",
  "exception_type": "ValidationError",
  "exception_message": "...",
  "traceback": "..." (solo en development)
}
```

### Rotación de Logs

Configura logrotate en `/etc/logrotate.d/taller_api`:

```
/var/log/taller_api/*.log {
    daily
    rotate 30
    compress
    delaycompress
    notifempty
    missingok
    create 0644 usuario usuario
    postrotate
        systemctl reload gunicorn-taller-api || true
    endscript
}
```

## Métricas de Aplicación

### Métricas Clave a Monitorear

1. **Autenticación**:
   - Tasa de login exitoso vs fallido
   - Tiempo promedio de autenticación
   - Tokens generados por minuto
   - Tokens en blacklist

2. **Rate Limiting**:
   - Requests bloqueados por rate limiting (429)
   - IPs con más requests bloqueados
   - Endpoints más afectados

3. **Performance**:
   - Tiempo de respuesta por endpoint
   - Queries lentas (>500ms)
   - Uso de CPU y memoria
   - Conexiones activas a BD

4. **Seguridad**:
   - Intentos de brute force detectados
   - Alertas de seguridad generadas
   - Tokens reutilizados después de logout
   - Abuso de password reset

### Queries SQL para Métricas

#### Tasa de Login Exitoso

```sql
SELECT 
    DATE(created_at) as fecha,
    COUNT(CASE WHEN action = 'LOGIN' THEN 1 END) as exitosos,
    COUNT(CASE WHEN action = 'LOGIN_FAILED' THEN 1 END) as fallidos,
    ROUND(
        COUNT(CASE WHEN action = 'LOGIN' THEN 1 END)::numeric / 
        NULLIF(COUNT(*), 0) * 100, 
        2
    ) as tasa_exito
FROM audit_log
WHERE action IN ('LOGIN', 'LOGIN_FAILED')
  AND created_at > NOW() - INTERVAL '7 days'
GROUP BY DATE(created_at)
ORDER BY fecha DESC;
```

#### IPs con Más Intentos Fallidos

```sql
SELECT 
    ip_address,
    COUNT(*) as intentos,
    MAX(created_at) as ultimo_intento
FROM audit_log
WHERE action = 'LOGIN_FAILED'
  AND created_at > NOW() - INTERVAL '24 hours'
GROUP BY ip_address
HAVING COUNT(*) > 5
ORDER BY intentos DESC
LIMIT 20;
```

#### Alertas de Seguridad Recientes

```sql
SELECT 
    created_at,
    ip_address,
    details->>'alert_type' as tipo_alerta,
    details->>'message' as mensaje
FROM audit_log
WHERE action = 'SECURITY_ALERT'
  AND created_at > NOW() - INTERVAL '7 days'
ORDER BY created_at DESC;
```

#### Tokens Activos en Blacklist

```sql
SELECT 
    COUNT(*) as tokens_activos,
    COUNT(CASE WHEN expires_at < NOW() THEN 1 END) as tokens_expirados
FROM token_blacklist;
```

## Alertas de Seguridad

### Eventos que Generan Alertas

El sistema genera alertas automáticas para:

1. **Brute Force**: >5 intentos de login fallidos en 10 minutos desde misma IP
2. **Token Reuse**: Uso de token después de logout
3. **Password Reset Abuse**: >3 solicitudes de reset en 1 hora desde mismo email

### Configurar Notificaciones por Email

Crea un script para enviar alertas por email cuando se detectan eventos críticos:

**Script**: `scripts/check_security_alerts.py`

```python
#!/usr/bin/env python
import sys
import os
from datetime import datetime, timezone, timedelta
import smtplib
from email.mime.text import MIMEText

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.base_datos import SessionLocal
from app.modelos.audit_log import AuditLog
from app.configuracion.config import SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_FROM

def check_and_notify_alerts():
    """Verifica alertas recientes y envía notificación si hay nuevas."""
    db = SessionLocal()
    try:
        # Buscar alertas de las últimas 24 horas
        cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
        
        alerts = db.query(AuditLog).filter(
            AuditLog.action == 'SECURITY_ALERT',
            AuditLog.created_at >= cutoff
        ).all()
        
        if not alerts:
            print("No hay alertas nuevas.")
            return
        
        # Construir mensaje
        message_lines = [
            f"Se detectaron {len(alerts)} alertas de seguridad en las últimas 24 horas:",
            "",
        ]
        
        for alert in alerts:
            message_lines.append(f"- [{alert.created_at}] {alert.details.get('alert_type', 'UNKNOWN')}")
            message_lines.append(f"  IP: {alert.ip_address}")
            message_lines.append(f"  Detalles: {alert.details.get('message', 'N/A')}")
            message_lines.append("")
        
        message_text = "\n".join(message_lines)
        
        # Enviar email
        msg = MIMEText(message_text)
        msg['Subject'] = f'[ALERTA] {len(alerts)} alertas de seguridad detectadas'
        msg['From'] = SMTP_FROM
        msg['To'] = 'admin@taller.com'  # Configurar email del admin
        
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)
        
        print(f"Notificación enviada: {len(alerts)} alertas.")
        
    finally:
        db.close()

if __name__ == "__main__":
    check_and_notify_alerts()
```

**Configuración cron** (cada hora):
```cron
0 * * * * cd /ruta/a/taller_api && /ruta/a/venv/bin/python scripts/check_security_alerts.py >> /var/log/taller_api/security_alerts.log 2>&1
```

### Integración con Servicios de Monitoreo

#### Sentry (Recomendado)

Para capturar errores automáticamente:

1. Instalar SDK:
   ```bash
   pip install sentry-sdk[fastapi]
   ```

2. Configurar en `app/main.py`:
   ```python
   import sentry_sdk
   from sentry_sdk.integrations.fastapi import FastApiIntegration
   
   if ENVIRONMENT == "production":
       sentry_sdk.init(
           dsn="tu-sentry-dsn",
           integrations=[FastApiIntegration()],
           traces_sample_rate=0.1,
           environment=ENVIRONMENT,
       )
   ```

3. Agregar a `.env`:
   ```
   SENTRY_DSN=https://...@sentry.io/...
   ```

#### Prometheus + Grafana

Para métricas en tiempo real:

1. Instalar prometheus-fastapi-instrumentator:
   ```bash
   pip install prometheus-fastapi-instrumentator
   ```

2. Configurar en `app/main.py`:
   ```python
   from prometheus_fastapi_instrumentator import Instrumentator
   
   app = FastAPI()
   
   # Instrumentar con Prometheus
   Instrumentator().instrument(app).expose(app, endpoint="/metrics")
   ```

3. Configurar Prometheus para scrape:
   ```yaml
   # prometheus.yml
   scrape_configs:
     - job_name: 'taller_api'
       static_configs:
         - targets: ['localhost:8000']
       metrics_path: '/metrics'
   ```

4. Crear dashboard en Grafana con métricas:
   - Request rate por endpoint
   - Response time percentiles (p50, p95, p99)
   - Error rate
   - Active connections

## Alertas Críticas

### Configurar Alertas en Prometheus

Crea `prometheus_alerts.yml`:

```yaml
groups:
  - name: taller_api_alerts
    interval: 1m
    rules:
      # Alta tasa de errores
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.05
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Alta tasa de errores en Taller API"
          description: "Más del 5% de requests están fallando"
      
      # Muchos intentos de login fallidos
      - alert: BruteForceAttempt
        expr: rate(http_requests_total{path="/auth/login",status="401"}[5m]) > 1
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "Posible ataque de brute force"
          description: "Múltiples intentos de login fallidos detectados"
      
      # Rate limiting excesivo
      - alert: HighRateLimiting
        expr: rate(http_requests_total{status="429"}[5m]) > 10
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Rate limiting excesivo"
          description: "Muchos requests están siendo bloqueados por rate limiting"
      
      # Tiempo de respuesta alto
      - alert: HighResponseTime
        expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Tiempo de respuesta alto"
          description: "P95 de tiempo de respuesta > 1 segundo"
```

### Notificaciones

Configura Alertmanager para enviar notificaciones:

```yaml
# alertmanager.yml
route:
  receiver: 'email-admin'
  group_by: ['alertname']
  group_wait: 10s
  group_interval: 10m
  repeat_interval: 12h

receivers:
  - name: 'email-admin'
    email_configs:
      - to: 'admin@taller.com'
        from: 'alertas@taller.com'
        smarthost: 'smtp.gmail.com:587'
        auth_username: 'alertas@taller.com'
        auth_password: 'tu_password'
```

## Health Checks

### Endpoint de Health Check

El sistema debe incluir un endpoint `/health` que verifica:

```python
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        # Verificar conexión a BD
        db = SessionLocal()
        db.execute("SELECT 1")
        db.close()
        
        return {
            "status": "healthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "version": "1.0.0",
            "database": "connected"
        }
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error": str(e)
            }
        )
```

### Monitoreo Externo

Configura servicios externos para verificar disponibilidad:

1. **UptimeRobot** (gratuito):
   - Monitorea `/health` cada 5 minutos
   - Envía alertas por email/SMS si el servicio cae

2. **Pingdom**:
   - Monitoreo desde múltiples ubicaciones
   - Alertas configurables

3. **StatusCake**:
   - Monitoreo de uptime y performance
   - Dashboard público opcional

## Dashboards Recomendados

### Dashboard de Seguridad (Grafana)

Paneles sugeridos:

1. **Login Activity**:
   - Logins exitosos vs fallidos (últimas 24h)
   - Tasa de éxito de login
   - Top 10 IPs con más intentos fallidos

2. **Security Alerts**:
   - Alertas por tipo (brute force, token reuse, etc.)
   - Timeline de alertas
   - IPs con alertas

3. **Rate Limiting**:
   - Requests bloqueados por endpoint
   - Top IPs bloqueados
   - Tendencia de rate limiting

4. **Audit Trail**:
   - Eventos por tipo
   - Actividad por usuario
   - Cambios en configuración sensible

### Dashboard de Performance

Paneles sugeridos:

1. **Request Metrics**:
   - Request rate (req/s)
   - Response time (p50, p95, p99)
   - Error rate por endpoint

2. **Database**:
   - Conexiones activas
   - Query time
   - Slow queries (>500ms)

3. **System Resources**:
   - CPU usage
   - Memory usage
   - Disk I/O

## Alertas Configuradas

### Alertas Críticas (Requieren Acción Inmediata)

1. **Sistema Caído**: Health check falla por >2 minutos
2. **Error Rate >10%**: Más del 10% de requests fallan
3. **Base de Datos Inaccesible**: Conexión a BD falla
4. **Disco Lleno**: Espacio en disco <10%

### Alertas de Advertencia (Revisar Pronto)

1. **Brute Force Detectado**: >5 intentos fallidos desde misma IP
2. **Rate Limiting Alto**: >100 requests bloqueados en 5 minutos
3. **Response Time Alto**: P95 >1 segundo por >5 minutos
4. **Memoria Alta**: Uso de memoria >80%

### Alertas Informativas (Revisar Regularmente)

1. **Nuevas Alertas de Seguridad**: Cualquier SECURITY_ALERT en audit_log
2. **Usuarios Desactivados**: Usuario desactivado por admin
3. **Cambios de Roles**: Roles de usuario modificados
4. **Tokens Blacklisted**: Spike en tokens invalidados

## Configuración de Alertas por Email

### Script de Verificación de Alertas

Ya incluido en `scripts/check_security_alerts.py` (ver CRON_JOBS.md).

### Configurar Múltiples Destinatarios

Edita el script para enviar a múltiples admins:

```python
recipients = ['admin1@taller.com', 'admin2@taller.com', 'seguridad@taller.com']
msg['To'] = ', '.join(recipients)
```

### Configurar Niveles de Alerta

```python
# Alertas críticas: enviar inmediatamente
if alert_type in ['BRUTE_FORCE', 'TOKEN_REUSE']:
    send_email(recipients=['admin@taller.com'], priority='high')

# Alertas de advertencia: agrupar y enviar cada hora
elif alert_type in ['PASSWORD_RESET_ABUSE']:
    queue_alert(alert)  # Enviar en batch
```

## Monitoreo de Logs en Tiempo Real

### Usando tail

```bash
# Ver logs de error en tiempo real
tail -f /var/log/taller_api/error.log

# Ver logs de acceso
tail -f /var/log/taller_api/access.log

# Filtrar solo errores 5xx
tail -f /var/log/taller_api/access.log | grep " 5[0-9][0-9] "
```

### Usando journalctl (systemd)

Si usas systemd para gestionar el servicio:

```bash
# Ver logs del servicio
journalctl -u taller-api -f

# Ver logs de las últimas 24 horas
journalctl -u taller-api --since "24 hours ago"

# Ver solo errores
journalctl -u taller-api -p err
```

## Herramientas de Monitoreo Recomendadas

### Opción 1: Stack Completo (Prometheus + Grafana + Alertmanager)

**Ventajas**:
- Métricas en tiempo real
- Dashboards personalizables
- Alertas configurables
- Open source y gratuito

**Instalación**:
```bash
# Docker Compose
docker-compose up -d prometheus grafana alertmanager
```

### Opción 2: Sentry (Solo Errores)

**Ventajas**:
- Fácil de configurar
- Captura automática de excepciones
- Stack traces completos
- Plan gratuito disponible

**Instalación**:
```bash
pip install sentry-sdk[fastapi]
```

### Opción 3: Datadog (Comercial)

**Ventajas**:
- Todo en uno (logs, métricas, traces)
- APM integrado
- Alertas inteligentes
- Soporte empresarial

**Instalación**:
```bash
pip install ddtrace
```

### Opción 4: ELK Stack (Elasticsearch + Logstash + Kibana)

**Ventajas**:
- Búsqueda avanzada de logs
- Visualizaciones potentes
- Análisis de logs históricos

**Desventajas**:
- Complejo de configurar
- Requiere recursos significativos

## Checklist de Configuración

- [ ] Logs de aplicación configurados y rotando
- [ ] Health check endpoint funcionando
- [ ] Métricas de Prometheus expuestas (si aplica)
- [ ] Dashboards de Grafana creados (si aplica)
- [ ] Alertas de seguridad configuradas
- [ ] Notificaciones por email funcionando
- [ ] Monitoreo externo configurado (UptimeRobot, etc.)
- [ ] Tareas periódicas en cron configuradas
- [ ] Rotación de logs configurada
- [ ] Documentación de runbooks para incidentes

## Runbooks para Incidentes

### Sistema Caído

1. Verificar que el proceso está corriendo: `ps aux | grep uvicorn`
2. Verificar logs: `tail -100 /var/log/taller_api/error.log`
3. Verificar conexión a BD: `psql -U postgres -d taller_db -c "SELECT 1;"`
4. Reiniciar servicio: `systemctl restart taller-api`
5. Si persiste, ejecutar rollback: `bash scripts/rollback.sh`

### Alta Tasa de Errores

1. Identificar endpoint problemático en logs
2. Verificar si es un problema de BD o lógica de negocio
3. Revisar cambios recientes: `git log --oneline -10`
4. Si es crítico, ejecutar rollback
5. Investigar y corregir el problema

### Ataque de Brute Force

1. Identificar IP atacante en audit_log
2. Bloquear IP en firewall: `sudo ufw deny from <IP>`
3. Verificar que rate limiting está funcionando
4. Revisar si hay otros IPs sospechosos
5. Considerar reducir límites temporalmente

### Base de Datos Lenta

1. Identificar queries lentas: `SELECT * FROM pg_stat_statements ORDER BY mean_exec_time DESC;`
2. Verificar índices: `SELECT * FROM pg_stat_user_indexes;`
3. Analizar plan de ejecución: `EXPLAIN ANALYZE <query>;`
4. Optimizar queries problemáticas
5. Considerar agregar índices

## Recursos Adicionales

- [Documentación de Prometheus](https://prometheus.io/docs/)
- [Documentación de Grafana](https://grafana.com/docs/)
- [Sentry para Python](https://docs.sentry.io/platforms/python/)
- [FastAPI Monitoring Best Practices](https://fastapi.tiangolo.com/advanced/monitoring/)
