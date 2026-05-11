---
inclusion: auto
---

# Docker Workflow - Taller API

## 🐳 Entorno de Desarrollo

Este proyecto usa **Docker para desarrollo** mediante WSL 2 (Ubuntu en Windows).

### Configuración actual:
- **Sistema:** Windows con WSL 2 + Ubuntu
- **Docker:** Instalado en Ubuntu (WSL)
- **Proyecto:** `/mnt/c/taller_api_v3` (accesible desde Ubuntu)
- **Compose file:** `docker-compose.dev.yml`

---

## 📋 Comandos Docker Estándar

### Opción A: Scripts PowerShell (Recomendado para Windows)

El usuario tiene scripts PowerShell que simplifican el workflow:

```powershell
# Iniciar todo el entorno
.\scripts\dev-start.ps1

# Ver logs de un servicio
.\scripts\dev-logs.ps1 backend

# Detener todo
.\scripts\dev-stop.ps1

# Ejecutar migraciones
.\scripts\dev-migrate.ps1

# Abrir shell en contenedor
.\scripts\dev-shell.ps1

# Reset completo (ELIMINA DATOS)
.\scripts\dev-reset.ps1
```

### Opción B: Comandos Docker directos (Desde Ubuntu/WSL)

```bash
# Iniciar servicios
cd /mnt/c/taller_api_v3
sudo docker compose -f docker-compose.dev.yml up -d

# Ver logs
sudo docker compose -f docker-compose.dev.yml logs -f backend

# Detener servicios
sudo docker compose -f docker-compose.dev.yml down

# Reiniciar un servicio
sudo docker compose -f docker-compose.dev.yml restart backend

# Ejecutar comandos en contenedor
sudo docker compose -f docker-compose.dev.yml exec backend <comando>

# Ejecutar migraciones
sudo docker compose -f docker-compose.dev.yml exec backend alembic upgrade head

# Crear migración
sudo docker compose -f docker-compose.dev.yml exec backend alembic revision -m "descripcion"

# Ejecutar tests
sudo docker compose -f docker-compose.dev.yml exec backend pytest
```

---

## 🔧 Servicios Disponibles

- **backend** - FastAPI con APScheduler (puerto 8000)
  - Incluye sistema de jobs programados (limpieza de notificaciones)
  - Hot reload habilitado para desarrollo
- **frontend** - Vite dev server (puerto 5173)
  - Hot reload habilitado
- **db** - PostgreSQL 15 (puerto 5432)
- **redis** - Redis 7 (puerto 6379)
  - Usado para caché y token blacklist
- **celery_worker** - Celery worker
  - Procesa tareas asíncronas

---

## 📝 Flujo de Trabajo

### Edición de código:
- El usuario edita archivos en Windows (`C:\taller_api_v3`)
- Los cambios se reflejan automáticamente en Docker (hot reload)
- No necesita reiniciar servicios para cambios en código Python o React

### Cambios que requieren rebuild:
- Modificaciones a `requirements.txt`
- Modificaciones a `package.json`
- Cambios en `Dockerfile`

**Comando para rebuild:**
```bash
sudo docker compose -f docker-compose.dev.yml build
sudo docker compose -f docker-compose.dev.yml up -d
```

---

## 🚨 Reglas Importantes

1. **NUNCA sugerir ejecutar comandos Python directamente en Windows**
   - ❌ `python -m uvicorn app.main:app --reload`
   - ✅ `sudo docker compose -f docker-compose.dev.yml up -d`

2. **NUNCA sugerir instalar dependencias en Windows**
   - ❌ `pip install nueva-libreria`
   - ✅ Agregar a `requirements.txt` y hacer rebuild

3. **SIEMPRE usar comandos Docker para:**
   - Ejecutar migraciones
   - Ejecutar tests
   - Ejecutar scripts Python
   - Acceder a la base de datos

4. **Acceso a base de datos:**
   - ❌ `psql -U postgres -d taller_db` (en Windows)
   - ✅ `sudo docker compose -f docker-compose.dev.yml exec db psql -U postgres -d taller_db`

5. **Ver logs de aplicación:**
   - ❌ Buscar en terminal de uvicorn
   - ✅ `sudo docker compose -f docker-compose.dev.yml logs -f backend`

---

## 🔄 Troubleshooting

### Servicios no inician:
```bash
sudo docker compose -f docker-compose.dev.yml down
sudo docker compose -f docker-compose.dev.yml up -d
```

### Error de permisos:
```bash
sudo service docker start
```

### Reset completo (ELIMINA DATOS):
```bash
sudo docker compose -f docker-compose.dev.yml down -v
sudo docker compose -f docker-compose.dev.yml up -d
sudo docker compose -f docker-compose.dev.yml exec backend alembic upgrade head
```

### Ver estado de servicios:
```bash
sudo docker compose -f docker-compose.dev.yml ps
```

---

## 📍 URLs de Desarrollo

- **Backend API:** http://localhost:8000
- **Frontend:** http://localhost:5173
- **API Docs:** http://localhost:8000/docs
- **PostgreSQL:** localhost:5432
- **Redis:** localhost:6379

---

## 💡 Recordatorios para Kiro

### Comandos y Workflow:
- **SIEMPRE** sugerir comandos Docker, nunca Python local
- Cuando el usuario pida ejecutar algo, usar `.\scripts\dev-*.ps1` o comandos Docker
- Cuando el usuario reporte un error, revisar logs con `.\scripts\dev-logs.ps1 backend`
- Cuando se agreguen dependencias, recordar hacer rebuild
- Cuando se modifique la BD, usar comandos Docker para migraciones
- El usuario edita en Windows, pero todo corre en Docker (WSL)

### Contexto Importante del Proyecto:
- **APScheduler está configurado** - El backend tiene jobs programados (limpieza de notificaciones diaria a las 00:00)
- **Bug de logout arreglado** - El `TokenBlacklistRepository` ya no permite duplicados (constraint único en Redis)
- **Multi-tenant estricto** - Todo debe filtrar por `taller_id` del JWT, nunca del body
- **Arquitectura:** FastAPI + PostgreSQL + Redis + Celery + APScheduler

### Verificaciones al iniciar:
Cuando el usuario inicie Docker, verificar en logs que aparezca:
```
✅ Configuración validada correctamente
✓ Caché Redis inicializado correctamente
✅ Scheduler de jobs iniciado correctamente
   - Limpieza de notificaciones: diaria a las 00:00
```

### Troubleshooting común:
- **Error "Port already in use"** → Detener proceso local que usa el puerto
- **Error "Cannot connect to database"** → Esperar 10 segundos y reintentar
- **Error de migraciones** → Verificar que la BD esté lista antes de migrar
- **Cambios no se reflejan** → Verificar hot reload, si no funciona reiniciar servicio
