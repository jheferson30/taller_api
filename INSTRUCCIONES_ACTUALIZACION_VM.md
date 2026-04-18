# 🚀 Instrucciones para Actualizar la VM de Azure

**Fecha:** 18 de Abril de 2026  
**Tiempo estimado:** 2-3 minutos  
**Downtime:** ~30 segundos

---

## ✅ CAMBIOS QUE SE VAN A APLICAR

1. ✅ Endpoint `/health` para healthchecks de Docker
2. ✅ Endpoint `/info` para información del servicio
3. ✅ Endpoint `/ping` para verificación rápida
4. ✅ Celery Worker para tareas asíncronas
5. ✅ Healthcheck en contenedor de API
6. ✅ Límites de recursos (CPU y memoria)
7. ✅ Dependencia `email-validator` agregada

---

## 📋 OPCIÓN 1: ACTUALIZACIÓN INCREMENTAL (RECOMENDADA)

**Ventajas:**
- ✅ Mantiene la base de datos intacta
- ✅ No pierdes datos
- ✅ Downtime mínimo (~30 segundos)
- ✅ Rápido (2 minutos)

### Paso 1: Conectarse a la VM

```bash
ssh azureuser@68.155.145.217
```

### Paso 2: Navegar al proyecto

```bash
cd ~/taller_api
```

### Paso 3: Cargar variables de entorno

```bash
set -a
source .env.production
set +a
```

### Paso 4: Traer cambios del repositorio

```bash
git pull origin main
```

**Deberías ver:**
```
remote: Enumerating objects...
Updating cea93f7..ca3ffd6
Fast-forward
 app/main.py                  |   3 +-
 app/rutas/health.py          | 100 +++++++++++++++++++
 docker-compose.prod.yml      | 152 ++++++++++++++++++++++++++
 ...
```

### Paso 5: Reconstruir imagen de la API

```bash
docker compose -f docker-compose.prod.yml build --no-cache api celery_worker
```

**Esto tardará 3-5 minutos.** Verás:
```
[+] Building 180.5s (29/29) FINISHED
```

### Paso 6: Actualizar servicios

```bash
# Levantar nuevos servicios (Celery Worker)
docker compose -f docker-compose.prod.yml up -d

# Esto detectará cambios y actualizará solo lo necesario
```

### Paso 7: Verificar que todo funciona

```bash
# Ver estado de contenedores
docker compose -f docker-compose.prod.yml ps
```

**Deberías ver 5 contenedores:**
```
NAME                    STATUS
taller-api              Up (healthy)
taller-celery-worker    Up (healthy)
taller-db               Up (healthy)
taller-nginx            Up
taller-redis            Up (healthy)
```

```bash
# Probar endpoint de health
curl http://localhost:8000/health
```

**Deberías ver:**
```json
{
  "status": "healthy",
  "service": "mecaapp-api",
  "timestamp": "2026-04-18T...",
  "checks": {
    "database": "healthy",
    "redis": "healthy"
  }
}
```

```bash
# Ver logs de la API
docker compose -f docker-compose.prod.yml logs api --tail=30
```

**Deberías ver:**
```
✅ Base de datos lista
🔨 Inicializando schema de base de datos...
✅ Schema inicializado
🔄 Ejecutando migraciones...
✅ Migraciones completadas
👤 Verificando usuario admin y roles...
✅ Usuario admin ya existe
🌐 Iniciando servidor...
```

### Paso 8: Probar desde el navegador

```
http://68.155.145.217/health
http://68.155.145.217/info
http://68.155.145.217/docs
```

---

## 📋 OPCIÓN 2: REINICIO COMPLETO (Solo si hay problemas)

**Usa esta opción solo si:**
- La Opción 1 falla
- Quieres empezar limpio
- Tienes problemas extraños

### Pasos:

```bash
cd ~/taller_api

# Cargar variables
set -a
source .env.production
set +a

# Traer cambios
git pull origin main

# Detener todo
docker compose -f docker-compose.prod.yml down

# Reconstruir todo
docker compose -f docker-compose.prod.yml build --no-cache

# Levantar todo
docker compose -f docker-compose.prod.yml up -d

# Esperar 30 segundos
sleep 30

# Verificar
docker compose -f docker-compose.prod.yml ps
curl http://localhost:8000/health
```

---

## 🐛 SOLUCIÓN DE PROBLEMAS

### Problema 1: "Container is restarting"

```bash
# Ver logs para identificar el error
docker compose -f docker-compose.prod.yml logs api --tail=50

# Si es problema de variables de entorno:
set -a
source .env.production
set +a
docker compose -f docker-compose.prod.yml restart api
```

### Problema 2: "email-validator is not installed"

```bash
# Reconstruir imagen sin caché
docker compose -f docker-compose.prod.yml build --no-cache api
docker compose -f docker-compose.prod.yml up -d api
```

### Problema 3: "relation 'users' does not exist"

```bash
# Ejecutar inicialización de BD manualmente
docker compose -f docker-compose.prod.yml exec api python scripts/init_database.py
docker compose -f docker-compose.prod.yml restart api
```

### Problema 4: Celery Worker no arranca

```bash
# Ver logs de Celery
docker compose -f docker-compose.prod.yml logs celery_worker --tail=50

# Reiniciar Celery
docker compose -f docker-compose.prod.yml restart celery_worker
```

### Problema 5: "502 Bad Gateway" en Nginx

```bash
# Verificar que la API está corriendo
docker compose -f docker-compose.prod.yml ps api

# Ver logs de Nginx
docker compose -f docker-compose.prod.yml logs nginx --tail=30

# Reiniciar Nginx
docker compose -f docker-compose.prod.yml restart nginx
```

---

## ✅ VERIFICACIÓN FINAL

### Checklist de Verificación:

- [ ] 5 contenedores corriendo (api, db, redis, nginx, celery_worker)
- [ ] API responde en `/health` con status "healthy"
- [ ] API responde en `/info` con información del servicio
- [ ] API responde en `/docs` con documentación Swagger
- [ ] No hay errores en logs: `docker compose -f docker-compose.prod.yml logs --tail=50`
- [ ] Celery Worker está "healthy": `docker compose -f docker-compose.prod.yml ps celery_worker`

### Comandos de Verificación Rápida:

```bash
# Todo en uno
echo "=== ESTADO DE CONTENEDORES ===" && \
docker compose -f docker-compose.prod.yml ps && \
echo -e "\n=== HEALTH CHECK ===" && \
curl -s http://localhost:8000/health | python3 -m json.tool && \
echo -e "\n=== INFO ===" && \
curl -s http://localhost:8000/info | python3 -m json.tool
```

---

## 📊 ANTES vs DESPUÉS

### ANTES:
```
✅ API funcionando
✅ PostgreSQL funcionando
✅ Redis funcionando
✅ Nginx funcionando
❌ Sin healthchecks
❌ Sin Celery Worker
❌ Sin límites de recursos
❌ Faltaba email-validator
```

### DESPUÉS:
```
✅ API funcionando
✅ PostgreSQL funcionando
✅ Redis funcionando
✅ Nginx funcionando
✅ Healthchecks en todos los servicios
✅ Celery Worker funcionando
✅ Límites de recursos configurados
✅ email-validator instalado
✅ Endpoints /health, /info, /ping
```

---

## 🎯 PRÓXIMOS PASOS (OPCIONAL)

### 1. Configurar HTTPS (Recomendado para producción)

```bash
# Instalar Certbot
sudo apt update
sudo apt install certbot python3-certbot-nginx

# Obtener certificado SSL (requiere dominio)
sudo certbot --nginx -d tu-dominio.com

# Renovación automática
sudo certbot renew --dry-run
```

### 2. Configurar Backups Automáticos

```bash
# Crear script de backup
cat > ~/backup_db.sh << 'EOF'
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
docker compose -f ~/taller_api/docker-compose.prod.yml exec -T db \
  pg_dump -U postgres taller_db > ~/backups/taller_db_$DATE.sql
# Mantener solo últimos 7 días
find ~/backups -name "taller_db_*.sql" -mtime +7 -delete
EOF

chmod +x ~/backup_db.sh

# Agregar a crontab (diario a las 2 AM)
(crontab -l 2>/dev/null; echo "0 2 * * * ~/backup_db.sh") | crontab -
```

### 3. Monitoreo con Prometheus (Avanzado)

Ver documentación en `docs/MONITOREO_Y_ALERTAS.md`

---

## 📞 SOPORTE

Si tienes problemas:

1. **Ver logs completos:**
   ```bash
   docker compose -f docker-compose.prod.yml logs --tail=100
   ```

2. **Reiniciar todo:**
   ```bash
   docker compose -f docker-compose.prod.yml restart
   ```

3. **Contactar soporte:**
   - Email: jefersoncely0@gmail.com
   - WhatsApp: +57 314 571 9752

---

**¡Listo! Tu sistema Docker está 100% completo y optimizado para producción.** 🎉
