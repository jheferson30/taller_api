# 🚀 Guía de Despliegue - MecaApp

## 📋 Requisitos Previos

- Docker y Docker Compose instalados
- Archivo `.env.production` configurado (ver `.env.production.example`)

## 🔧 Configuración Inicial

### 1. Crear archivo de configuración de producción

```bash
cp .env.production.example .env.production
```

### 2. Configurar variables críticas en `.env.production`

**Variables OBLIGATORIAS que debes cambiar:**

```bash
# Contraseña de PostgreSQL
DB_PASSWORD=tu_contrasena_segura_aqui

# Actualizar en DATABASE_URL también
DATABASE_URL=postgresql+psycopg2://postgres:tu_contrasena_segura_aqui@db:5432/taller_db?client_encoding=utf8

# Contraseña del usuario admin
ADMIN_PASSWORD=tu_contrasena_admin_aqui

# Contraseña para PDFs
PDF_PASSWORD=tu_contrasena_pdf_aqui

# IP pública de tu servidor
PUBLIC_IP=tu_ip_publica_aqui

# Orígenes permitidos (CORS)
ALLOWED_ORIGINS=http://tu_ip_publica_aqui
ALLOWED_HOSTS=tu_ip_publica_aqui
```

**Generar claves secretas seguras:**

```bash
# JWT Secret Key
python3 -c "import secrets; print('JWT_SECRET_KEY=' + secrets.token_urlsafe(32))"

# CSRF Secret Key
python3 -c "import secrets; print('CSRF_SECRET_KEY=' + secrets.token_urlsafe(32))"
```

Copia las claves generadas y pégalas en `.env.production`.

## 🐳 Despliegue con Docker

### Opción 1: Usar el script de despliegue automático

```bash
bash deploy.sh
```

Este script:
- ✅ Instala Docker si no está instalado
- ✅ Verifica que `.env.production` existe
- ✅ Construye las imágenes Docker
- ✅ Levanta todos los servicios
- ✅ Inicializa la base de datos automáticamente
- ✅ Crea el usuario admin

### Opción 2: Despliegue manual

```bash
# 1. Construir las imágenes
docker compose -f docker-compose.prod.yml build

# 2. Levantar los servicios
docker compose -f docker-compose.prod.yml up -d

# 3. Verificar el estado
docker compose -f docker-compose.prod.yml ps

# 4. Ver logs
docker compose -f docker-compose.prod.yml logs -f api
```

## 🔍 Verificación del Despliegue

### Verificar que todos los servicios están corriendo

```bash
docker compose -f docker-compose.prod.yml ps
```

Deberías ver:
- ✅ `taller-api` - Estado: `Up` (healthy)
- ✅ `taller-db` - Estado: `Up` (healthy)
- ✅ `taller-redis` - Estado: `Up` (healthy)
- ✅ `taller-nginx` - Estado: `Up`

### Verificar logs de la API

```bash
docker compose -f docker-compose.prod.yml logs api --tail=50
```

Deberías ver:
```
✅ Base de datos lista
🔨 Inicializando schema de base de datos...
✅ Schema inicializado
🔄 Ejecutando migraciones...
✅ Migraciones completadas
👤 Verificando usuario admin y roles...
✅ Usuario admin creado exitosamente
🌐 Iniciando servidor...
```

### Probar la API

```bash
# Desde el servidor
curl http://localhost:8000/docs

# Desde tu navegador
http://TU_IP_PUBLICA/docs
```

## 🔄 Actualizar el Despliegue

```bash
# 1. Detener servicios
docker compose -f docker-compose.prod.yml down

# 2. Actualizar código (git pull, etc.)
git pull origin main

# 3. Reconstruir imágenes
docker compose -f docker-compose.prod.yml build --no-cache

# 4. Levantar servicios
docker compose -f docker-compose.prod.yml up -d
```

## 🛠️ Comandos Útiles

### Ver logs en tiempo real

```bash
docker compose -f docker-compose.prod.yml logs -f
```

### Reiniciar un servicio específico

```bash
docker compose -f docker-compose.prod.yml restart api
```

### Ejecutar comandos dentro del contenedor

```bash
# Abrir shell en el contenedor de la API
docker compose -f docker-compose.prod.yml exec api bash

# Ejecutar migraciones manualmente
docker compose -f docker-compose.prod.yml exec api alembic upgrade head

# Crear usuario admin manualmente
docker compose -f docker-compose.prod.yml exec api python scripts/seed_admin.py
```

### Backup de la base de datos

```bash
# Crear backup
docker compose -f docker-compose.prod.yml exec db pg_dump -U postgres taller_db > backup_$(date +%Y%m%d_%H%M%S).sql

# Restaurar backup
docker compose -f docker-compose.prod.yml exec -T db psql -U postgres taller_db < backup_20260418_120000.sql
```

### Limpiar todo y empezar de cero

```bash
# ⚠️ CUIDADO: Esto borra TODOS los datos
docker compose -f docker-compose.prod.yml down -v
docker compose -f docker-compose.prod.yml up -d
```

## 🐛 Solución de Problemas

### La API no arranca

```bash
# Ver logs detallados
docker compose -f docker-compose.prod.yml logs api --tail=100

# Verificar que la BD está lista
docker compose -f docker-compose.prod.yml exec db psql -U postgres -d taller_db -c "\dt"
```

### Error "relation does not exist"

Esto significa que las tablas no se crearon. Solución:

```bash
# Recrear las tablas
docker compose -f docker-compose.prod.yml exec api python scripts/init_database.py
docker compose -f docker-compose.prod.yml restart api
```

### Error "email-validator is not installed"

Esto significa que falta una dependencia. Solución:

```bash
# Reconstruir la imagen
docker compose -f docker-compose.prod.yml build --no-cache api
docker compose -f docker-compose.prod.yml up -d
```

### Puerto 80 ya está en uso

```bash
# Detener el servicio que usa el puerto 80
sudo systemctl stop nginx  # Si tienes nginx instalado en el host
sudo systemctl stop apache2  # Si tienes apache instalado en el host

# Luego reinicia los contenedores
docker compose -f docker-compose.prod.yml up -d
```

## 📞 Credenciales por Defecto

Después del primer despliegue:

- **Usuario:** `admin`
- **Contraseña:** La que configuraste en `ADMIN_PASSWORD` en `.env.production`
- **Email:** `admin@taller.local`

⚠️ **IMPORTANTE:** Cambia la contraseña después del primer login.

## 🔒 Seguridad

### Recomendaciones:

1. ✅ Usa contraseñas fuertes (mínimo 12 caracteres, mayúsculas, minúsculas, números, símbolos)
2. ✅ Genera claves JWT y CSRF únicas y seguras (32+ caracteres)
3. ✅ Configura HTTPS con certificados SSL (Let's Encrypt)
4. ✅ Configura firewall para permitir solo puertos necesarios (80, 443)
5. ✅ Mantén Docker y las imágenes actualizadas
6. ✅ Haz backups regulares de la base de datos
7. ✅ No compartas el archivo `.env.production` (está en `.gitignore`)

## 📚 Más Información

- Documentación de la API: `http://TU_IP/docs`
- Repositorio: [GitHub](https://github.com/tu-usuario/taller_api)
- Soporte: [Issues](https://github.com/tu-usuario/taller_api/issues)
