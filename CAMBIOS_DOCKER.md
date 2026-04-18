# 🔧 Cambios Realizados para Mejorar el Despliegue con Docker

## 📝 Resumen

Se han realizado mejoras significativas en el sistema de despliegue con Docker para que sea **completamente automático** y **sin errores**.

## ✅ Cambios Implementados

### 1. **Agregada dependencia faltante** (`requirements.txt`)
- ✅ Agregado `email-validator` que faltaba y causaba errores al iniciar la API

### 2. **Nuevo script de inicialización de base de datos** (`scripts/init_database.py`)
- ✅ Crea **todas las tablas automáticamente** desde los modelos SQLAlchemy
- ✅ Verifica qué tablas ya existen antes de crearlas
- ✅ Importa todos los modelos necesarios:
  - `User`, `Role`, `UserRole`
  - `AuditLog`, `TokenBlacklist`, `PasswordResetToken`
  - `Vehiculo`, `Ticket`, `TicketProceso`, `TicketRepuesto`, `TicketFoto`, `TicketCompra`, `TicketCobro`
  - `MovimientoCaja`, `CambioMovimientoCaja`
  - `Mecanico`, `Cita`
  - `ConfiguracionTaller`, `ConfiguracionSeguridad`
  - `LogNotificacion`, `AppConfig`

### 3. **Mejorado el entrypoint** (`scripts/entrypoint.sh`)
- ✅ Ahora ejecuta `init_database.py` **antes** de las migraciones de Alembic
- ✅ Garantiza que todas las tablas existan antes de intentar crear el usuario admin
- ✅ Orden de ejecución:
  1. Esperar a que PostgreSQL esté listo
  2. **Inicializar schema** (crear tablas si no existen)
  3. Ejecutar migraciones de Alembic
  4. Crear usuario admin y roles
  5. Iniciar servidor

### 4. **Mejorado el script de despliegue** (`deploy.sh`)
- ✅ Valida que `.env.production` existe
- ✅ Valida que las variables críticas están configuradas:
  - `DB_PASSWORD`
  - `ADMIN_PASSWORD`
  - `JWT_SECRET_KEY`
  - `CSRF_SECRET_KEY`
- ✅ Detiene servicios anteriores antes de reconstruir
- ✅ Espera 30 segundos para que los servicios estén completamente listos
- ✅ Verifica la salud de la API después del despliegue
- ✅ Muestra un resumen completo con URLs y comandos útiles
- ✅ Si Docker no está instalado, lo instala y pide reiniciar sesión

### 5. **Nueva documentación de despliegue** (`DEPLOY.md`)
- ✅ Guía completa paso a paso
- ✅ Instrucciones para generar claves secretas
- ✅ Comandos útiles para administración
- ✅ Solución de problemas comunes
- ✅ Recomendaciones de seguridad

## 🎯 Resultado Final

### Antes:
```
❌ Faltaba email-validator → API no arrancaba
❌ Migración vacía → No se creaban tablas
❌ seed_admin.py fallaba → No había tabla users
❌ API en loop de reinicio constante
❌ Despliegue manual y propenso a errores
```

### Ahora:
```
✅ Todas las dependencias incluidas
✅ Tablas se crean automáticamente desde modelos SQLAlchemy
✅ Usuario admin se crea correctamente
✅ API arranca sin errores
✅ Despliegue 100% automático con un solo comando
```

## 🚀 Cómo Usar

### Despliegue Completo (Un Solo Comando)

```bash
# 1. Configurar .env.production
cp .env.production.example .env.production
nano .env.production  # Editar variables críticas

# 2. Ejecutar script de despliegue
bash deploy.sh
```

¡Eso es todo! El script se encarga de:
- Instalar Docker si no está
- Validar configuración
- Construir imágenes
- Crear base de datos y tablas
- Crear usuario admin
- Levantar todos los servicios

### Verificar que Todo Funciona

```bash
# Ver estado de contenedores
docker compose -f docker-compose.prod.yml ps

# Ver logs de la API
docker compose -f docker-compose.prod.yml logs api --tail=50

# Probar la API
curl http://localhost:8000/docs
```

## 📊 Arquitectura del Despliegue

```
┌─────────────────────────────────────────────────────────┐
│                    deploy.sh                            │
│  (Orquesta todo el proceso de despliegue)               │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│              Docker Compose                             │
│  (Levanta contenedores: API, DB, Redis, Nginx)          │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│            scripts/entrypoint.sh                        │
│  (Se ejecuta al iniciar el contenedor de la API)        │
└────────────────────┬────────────────────────────────────┘
                     │
                     ├─► 1. Esperar PostgreSQL
                     │
                     ├─► 2. scripts/init_database.py
                     │      (Crea todas las tablas)
                     │
                     ├─► 3. alembic upgrade head
                     │      (Ejecuta migraciones)
                     │
                     ├─► 4. scripts/seed_admin.py
                     │      (Crea usuario admin)
                     │
                     └─► 5. Iniciar Gunicorn + Uvicorn
                            (API lista para recibir requests)
```

## 🔒 Seguridad

Los cambios también mejoran la seguridad:

- ✅ Validación de variables críticas antes del despliegue
- ✅ `.env.production` nunca se sube al repositorio (`.gitignore`)
- ✅ Generación de claves secretas únicas por instalación
- ✅ Documentación de mejores prácticas de seguridad

## 🐛 Problemas Resueltos

1. **"email-validator is not installed"**
   - ✅ Resuelto: Agregado a `requirements.txt`

2. **"relation 'users' does not exist"**
   - ✅ Resuelto: `init_database.py` crea todas las tablas automáticamente

3. **"Container is restarting"**
   - ✅ Resuelto: Entrypoint mejorado con orden correcto de inicialización

4. **Variables de entorno no se leen**
   - ✅ Resuelto: `docker-compose.prod.yml` configurado correctamente con `env_file`

5. **Despliegue manual propenso a errores**
   - ✅ Resuelto: Script `deploy.sh` automatiza y valida todo el proceso

## 📚 Archivos Modificados/Creados

### Modificados:
- ✅ `requirements.txt` - Agregado `email-validator`
- ✅ `scripts/entrypoint.sh` - Agregado paso de inicialización de schema
- ✅ `deploy.sh` - Mejorado con validaciones y mejor UX

### Creados:
- ✅ `scripts/init_database.py` - Script de inicialización de tablas
- ✅ `DEPLOY.md` - Documentación completa de despliegue
- ✅ `CAMBIOS_DOCKER.md` - Este archivo

## 🎓 Lecciones Aprendidas

1. **Docker debe ser completamente autónomo**: No debe requerir pasos manuales
2. **Validar antes de ejecutar**: Mejor fallar rápido con mensajes claros
3. **Documentar todo**: Una buena documentación ahorra horas de soporte
4. **Usar modelos SQLAlchemy como fuente de verdad**: Más confiable que scripts SQL manuales
5. **Orden de inicialización importa**: Schema → Migraciones → Seeds → Aplicación

## ✨ Próximos Pasos (Opcional)

- [ ] Agregar healthchecks más robustos
- [ ] Implementar backups automáticos de BD
- [ ] Agregar monitoreo con Prometheus/Grafana
- [ ] Configurar CI/CD con GitHub Actions
- [ ] Implementar rolling updates sin downtime

## 📞 Soporte

Si encuentras algún problema:

1. Revisa `DEPLOY.md` - Sección "Solución de Problemas"
2. Verifica logs: `docker compose -f docker-compose.prod.yml logs api`
3. Verifica estado: `docker compose -f docker-compose.prod.yml ps`

---

**Fecha de cambios:** 18 de Abril de 2026  
**Versión:** 2.0 - Despliegue Automático Completo
