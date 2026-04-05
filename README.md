# Taller API - Sistema de Gestión de Taller Mecánico

API REST para gestión de taller mecánico con autenticación JWT, sistema de roles, auditoría completa y modo offline para aplicaciones móviles.

## Características Principales

- **Autenticación JWT**: Sistema moderno con access tokens y refresh tokens
- **Sistema de Roles**: Control de acceso basado en roles (ADMIN, MECANICO, RECEPCIONISTA, SOLO_LECTURA)
- **Audit Trail**: Registro completo de eventos de seguridad y operaciones críticas
- **Rate Limiting**: Protección contra abuso con límites configurables
- **Modo Offline**: Sincronización por lotes para aplicaciones móviles
- **Arquitectura en Capas**: Separación clara entre rutas, servicios y repositorios
- **Hashing Seguro**: bcrypt para contraseñas con migración automática desde SHA256

## Requisitos

- Python 3.9+
- PostgreSQL 12+
- pip o poetry para gestión de dependencias

## Instalación

### 1. Clonar el repositorio

```bash
git clone <url-del-repositorio>
cd taller_api
```

### 2. Crear entorno virtual

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 4. Configurar variables de entorno

Copia el archivo de ejemplo y ajusta los valores:

```bash
cp .env.example .env
```

Edita `.env` y configura las variables requeridas (ver sección Variables de Entorno más abajo).

### 5. Configurar base de datos

Crea la base de datos en PostgreSQL:

```sql
CREATE DATABASE taller_db;
```

Ejecuta la migración:

```bash
psql -U postgres -d taller_db -f db/migracion_jwt_auth_2026_03_28.sql
```

### 6. Migrar contraseñas existentes (si aplica)

Si tienes usuarios existentes con contraseñas SHA256:

```bash
python scripts/migrate_passwords.py
```

Este script:
- Lee contraseñas de la tabla `configuracion_seguridad`
- Crea usuarios en la tabla `users` con hash SHA256 temporal
- Marca usuarios como `is_migrated=False`
- En el primer login exitoso, la contraseña se migra automáticamente a bcrypt

### 7. Iniciar el servidor

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

La API estará disponible en `http://localhost:8000`

Documentación interactiva: `http://localhost:8000/docs`

## Variables de Entorno

### Autenticación y Seguridad JWT

| Variable | Descripción | Valor por Defecto | Requerida |
|----------|-------------|-------------------|-----------|
| `JWT_SECRET_KEY` | Clave secreta para firmar tokens JWT (mínimo 32 caracteres) | - | ✅ |
| `JWT_ALGORITHM` | Algoritmo de firma JWT | `HS256` | ✅ |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | Tiempo de expiración del access token en minutos | `15` | ✅ |
| `JWT_REFRESH_TOKEN_EXPIRE_DAYS` | Tiempo de expiración del refresh token en días | `7` | ✅ |

**Generar JWT_SECRET_KEY segura**:
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### Contraseñas y Hashing

| Variable | Descripción | Valor por Defecto | Requerida |
|----------|-------------|-------------------|-----------|
| `PASSWORD_HASHER` | Algoritmo de hashing | `bcrypt` | ✅ |
| `BCRYPT_COST_FACTOR` | Factor de costo de bcrypt (4-31) | `12` | ✅ |
| `PASSWORD_MIN_LENGTH` | Longitud mínima de contraseña | `8` | ✅ |
| `PASSWORD_REQUIRE_UPPERCASE` | Requerir mayúscula | `true` | ✅ |
| `PASSWORD_REQUIRE_LOWERCASE` | Requerir minúscula | `true` | ✅ |
| `PASSWORD_REQUIRE_DIGIT` | Requerir dígito | `true` | ✅ |

**Nota**: En tests, usa `BCRYPT_COST_FACTOR=4` para mayor velocidad.

### Rate Limiting

| Variable | Descripción | Valor por Defecto | Requerida |
|----------|-------------|-------------------|-----------|
| `RATE_LIMIT_AUTH_PER_MINUTE` | Límite de requests de autenticación por minuto por IP | `5` | ✅ |
| `RATE_LIMIT_CREATE_PER_MINUTE` | Límite de requests de creación por minuto por usuario | `30` | ✅ |
| `RATE_LIMIT_READ_PER_MINUTE` | Límite de requests de lectura por minuto por usuario | `100` | ✅ |
| `RATE_LIMIT_WHITELIST_IPS` | IPs excluidas de rate limiting (separadas por comas) | `127.0.0.1,::1` | ❌ |

### Seguridad y Detección

| Variable | Descripción | Valor por Defecto | Requerida |
|----------|-------------|-------------------|-----------|
| `ENVIRONMENT` | Entorno de ejecución (`development` o `production`) | `development` | ✅ |
| `MAX_LOGIN_ATTEMPTS` | Máximo de intentos de login fallidos antes de alerta | `5` | ✅ |
| `LOGIN_ATTEMPT_WINDOW_MINUTES` | Ventana de tiempo para contar intentos (minutos) | `10` | ✅ |

### Recuperación de Contraseña

| Variable | Descripción | Valor por Defecto | Requerida |
|----------|-------------|-------------------|-----------|
| `PASSWORD_RESET_TOKEN_EXPIRE_HOURS` | Tiempo de expiración del token de reset (horas) | `1` | ✅ |
| `PASSWORD_RESET_MAX_REQUESTS_PER_HOUR` | Máximo de solicitudes de reset por hora por email | `3` | ✅ |

### Sesiones y Auditoría

| Variable | Descripción | Valor por Defecto | Requerida |
|----------|-------------|-------------------|-----------|
| `SESSION_TIMEOUT_MINUTES` | Tiempo de inactividad antes de cerrar sesión (minutos) | `30` | ✅ |
| `AUDIT_LOG_RETENTION_DAYS` | Días de retención de logs de auditoría (0 = infinito) | `90` | ✅ |

### Modo Legacy (Transición)

| Variable | Descripción | Valor por Defecto | Requerida |
|----------|-------------|-------------------|-----------|
| `ENABLE_LEGACY_AUTH` | Habilitar autenticación legacy SHA256 durante transición | `true` | ❌ |

**Nota**: Después de migrar todos los usuarios, deshabilita el modo legacy con `ENABLE_LEGACY_AUTH=false`.

### Email (SMTP)

| Variable | Descripción | Valor por Defecto | Requerida |
|----------|-------------|-------------------|-----------|
| `SMTP_HOST` | Host del servidor SMTP | - | ✅ |
| `SMTP_PORT` | Puerto del servidor SMTP | `587` | ✅ |
| `SMTP_USER` | Usuario SMTP | - | ✅ |
| `SMTP_PASSWORD` | Contraseña SMTP | - | ✅ |
| `SMTP_FROM` | Email remitente | - | ✅ |

### Base de Datos

| Variable | Descripción | Valor por Defecto | Requerida |
|----------|-------------|-------------------|-----------|
| `DATABASE_URL` | URL de conexión a PostgreSQL | - | ✅ |

**Formato**: `postgresql+psycopg2://usuario:contraseña@host:puerto/nombre_bd?client_encoding=utf8`

### Contraseñas Legacy (Compatibilidad)

| Variable | Descripción | Valor por Defecto | Requerida |
|----------|-------------|-------------------|-----------|
| `ADMIN_PASSWORD` | Contraseña para operaciones del sistema (legacy) | - | ❌ |
| `PDF_PASSWORD` | Contraseña para generar PDFs | - | ❌ |

### CORS

| Variable | Descripción | Valor por Defecto | Requerida |
|----------|-------------|-------------------|-----------|
| `ALLOWED_ORIGINS` | Orígenes permitidos para CORS (separados por comas) | `*` | ❌ |

**Ejemplo**: `http://localhost:3000,http://localhost:5173,https://taller.com`

## Proceso de Deployment

### Pre-Deployment Checklist

Antes de hacer deployment a producción, verifica:

- [ ] Todas las variables de entorno están configuradas en `.env`
- [ ] `JWT_SECRET_KEY` es una clave segura de al menos 32 caracteres
- [ ] `ENVIRONMENT=production` está configurado
- [ ] `BCRYPT_COST_FACTOR=12` para seguridad óptima
- [ ] Base de datos PostgreSQL está configurada y accesible
- [ ] Backup de base de datos está disponible
- [ ] Todos los tests pasan: `pytest`
- [ ] Análisis de seguridad ejecutado: `bandit -r app/`
- [ ] Dependencias actualizadas y sin vulnerabilidades: `safety check`

### Deployment Steps

#### 1. Backup de Base de Datos

```bash
pg_dump -U postgres -d taller_db > backup_$(date +%Y%m%d_%H%M%S).sql
```

#### 2. Ejecutar Migración de Base de Datos

```bash
psql -U postgres -d taller_db -f db/migracion_jwt_auth_2026_03_28.sql
```

Esto creará las tablas:
- `users` - Usuarios del sistema
- `roles` - Roles disponibles
- `user_roles` - Relación usuarios-roles
- `audit_log` - Registro de auditoría
- `token_blacklist` - Tokens invalidados
- `password_reset_tokens` - Tokens de recuperación de contraseña

#### 3. Migrar Contraseñas Existentes

Si tienes usuarios en `configuracion_seguridad`:

```bash
python scripts/migrate_passwords.py
```

Revisa el reporte de migración generado.

#### 4. Configurar Variables de Entorno de Producción

Edita `.env` y asegúrate de:
- Cambiar `JWT_SECRET_KEY` a un valor seguro único
- Configurar `ENVIRONMENT=production`
- Configurar credenciales SMTP reales
- Configurar `DATABASE_URL` con credenciales de producción
- Configurar `ALLOWED_ORIGINS` con dominios reales

#### 5. Instalar Dependencias de Producción

```bash
pip install -r requirements.txt
```

#### 6. Ejecutar Tests

```bash
# Tests unitarios y de integración
pytest

# Tests de property-based (opcional pero recomendado)
pytest tests/test_*_properties.py

# Verificar cobertura
pytest --cov=app --cov-report=html
```

#### 7. Análisis de Seguridad

```bash
# Análisis estático de seguridad
bandit -r app/

# Verificar vulnerabilidades en dependencias
safety check
```

#### 8. Iniciar Servidor

**Desarrollo**:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Producción** (con Gunicorn):
```bash
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

Parámetros recomendados:
- `-w 4`: 4 workers (ajustar según CPU cores)
- `-k uvicorn.workers.UvicornWorker`: Worker class para ASGI
- `--bind 0.0.0.0:8000`: Escuchar en todas las interfaces

#### 9. Configurar Reverse Proxy (Nginx)

Ejemplo de configuración Nginx:

```nginx
server {
    listen 80;
    server_name api.taller.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

#### 10. Configurar Tareas Periódicas (Cron)

Agrega a crontab:

```bash
# Limpieza de tokens blacklisted expirados (diario a las 2 AM)
0 2 * * * cd /ruta/a/taller_api && /ruta/a/venv/bin/python scripts/cleanup_blacklist.py

# Archival de audit logs (mensual, primer día del mes a las 3 AM)
0 3 1 * * cd /ruta/a/taller_api && /ruta/a/venv/bin/python scripts/archive_audit_logs.py

# Reporte de métricas de seguridad (semanal, lunes a las 8 AM)
0 8 * * 1 cd /ruta/a/taller_api && /ruta/a/venv/bin/python scripts/security_report.py
```

### Post-Deployment Verification

Después del deployment, verifica:

1. **Health Check**: `curl http://tu-servidor:8000/health`
2. **Login funciona**: Prueba login con usuario de prueba
3. **Refresh token funciona**: Prueba refresh de access token
4. **Rate limiting activo**: Verifica que límites se aplican
5. **Audit log registra eventos**: Verifica tabla `audit_log`
6. **Documentación accesible**: `http://tu-servidor:8000/docs`

### Rollback Plan

Si algo sale mal durante el deployment:

#### 1. Revertir Código

```bash
git checkout <commit-anterior>
```

#### 2. Habilitar Modo Legacy

Edita `.env`:
```
ENABLE_LEGACY_AUTH=true
```

Reinicia el servidor.

#### 3. Revertir Base de Datos (si es necesario)

```bash
psql -U postgres -d taller_db < backup_YYYYMMDD_HHMMSS.sql
```

**Nota**: Solo revertir base de datos si la migración causó problemas. Los usuarios migrados a bcrypt no podrán hacer login con el backup antiguo.

## Migración de Clientes

Para migrar aplicaciones cliente (móvil y web) al nuevo sistema JWT, consulta la guía completa:

📖 **[Guía de Migración a JWT](docs/MIGRACION_JWT.md)**

La guía incluye:
- Ejemplos de código para React Native y React
- Implementación de AuthService
- Manejo de refresh tokens automático
- Modo offline y sincronización por lotes
- Manejo de errores y rate limiting
- Guía paso a paso de migración

## Estructura del Proyecto

```
taller_api/
├── app/
│   ├── main.py                    # Aplicación FastAPI principal
│   ├── configuracion/             # Configuración y validación
│   │   └── config_validator.py
│   ├── modelos/                   # Modelos SQLAlchemy
│   │   ├── user.py
│   │   ├── role.py
│   │   ├── audit_log.py
│   │   └── ...
│   ├── esquemas/                  # Schemas Pydantic
│   │   ├── auth_schema.py
│   │   ├── user_schema.py
│   │   └── ...
│   ├── repositorios/              # Capa de acceso a datos
│   │   ├── user_repository.py
│   │   ├── ticket_repository.py
│   │   └── ...
│   ├── servicios/                 # Lógica de negocio
│   │   ├── auth_service.py
│   │   ├── user_service.py
│   │   ├── ticket_service.py
│   │   └── ...
│   ├── rutas/                     # Endpoints REST
│   │   ├── auth_ruta.py
│   │   ├── users_ruta.py
│   │   ├── ticket_ruta.py
│   │   └── ...
│   ├── seguridad/                 # Componentes de seguridad
│   │   ├── password_hasher.py
│   │   ├── token_manager.py
│   │   └── auth_middleware.py
│   └── utils/                     # Utilidades
│       └── exceptions.py
├── db/                            # Migraciones de base de datos
│   └── migracion_jwt_auth_2026_03_28.sql
├── scripts/                       # Scripts de utilidad
│   └── migrate_passwords.py
├── tests/                         # Tests
│   ├── test_auth_service.py
│   ├── test_auth_service_properties.py
│   └── ...
├── docs/                          # Documentación
│   └── MIGRACION_JWT.md
├── .env.example                   # Ejemplo de variables de entorno
├── requirements.txt               # Dependencias Python
└── README.md                      # Este archivo
```

## Arquitectura

El sistema sigue una arquitectura en capas:

1. **Rutas (Routes)**: Endpoints REST, parsing de requests, validación de schemas
2. **Servicios (Services)**: Lógica de negocio, orquestación, validaciones
3. **Repositorios (Repositories)**: Acceso a datos, queries SQL
4. **Modelos (Models)**: Definiciones de tablas SQLAlchemy

Esta separación permite:
- Reutilización de lógica entre endpoints
- Testing más fácil (mock de repositorios)
- Mantenibilidad y escalabilidad

## Sistema de Roles

El sistema incluye 4 roles predefinidos:

| Rol | Permisos |
|-----|----------|
| `ADMIN` | Acceso completo: gestión de usuarios, configuración, todas las operaciones |
| `MECANICO` | Crear y actualizar tickets, procesos, repuestos |
| `RECEPCIONISTA` | Crear tickets, citas, consultar información |
| `SOLO_LECTURA` | Solo consultar información, sin modificaciones |

Los roles se asignan en la tabla `user_roles` y se validan con el decorador `@require_role()`.

## Endpoints Principales

### Autenticación

- `POST /auth/login` - Iniciar sesión
- `POST /auth/refresh` - Refrescar access token
- `POST /auth/logout` - Cerrar sesión
- `POST /auth/forgot-password` - Solicitar recuperación de contraseña
- `POST /auth/reset-password` - Restablecer contraseña

### Usuarios (requiere rol ADMIN)

- `POST /users` - Crear usuario
- `GET /users` - Listar usuarios (paginado)
- `GET /users/{id}` - Obtener usuario
- `PATCH /users/{id}` - Actualizar usuario
- `DELETE /users/{id}` - Desactivar usuario (soft delete)
- `POST /users/me/change-password` - Cambiar contraseña propia

### Tickets

- `GET /api/mobile/tickets` - Listar tickets
- `POST /api/mobile/tickets` - Crear ticket
- `POST /api/mobile/tickets/{id}/procesos` - Agregar proceso
- `POST /api/mobile/tickets/{id}/repuestos` - Agregar repuesto
- `POST /api/mobile/tickets/{id}/finalizar` - Finalizar ticket
- `POST /api/mobile/tickets/{id}/entregar` - Entregar ticket

### Sincronización Offline (App Móvil)

- `POST /api/mobile/sync/batch` - Sincronizar operaciones offline por lotes

### Auditoría (requiere rol ADMIN)

- `GET /audit-log` - Consultar logs de auditoría (con filtros y paginación)

Ver documentación completa en: `http://localhost:8000/docs`

## Testing

### Ejecutar Todos los Tests

```bash
pytest
```

### Ejecutar Tests Específicos

```bash
# Tests de autenticación
pytest tests/test_auth_service.py

# Property-based tests
pytest tests/test_auth_service_properties.py

# Tests con cobertura
pytest --cov=app --cov-report=html
```

### Tests de Property-Based

El proyecto incluye tests de property-based usando Hypothesis para validar propiedades universales:

```bash
# Ejecutar solo property tests
pytest tests/test_*_properties.py -v
```

Estos tests validan propiedades como:
- Hashing de contraseñas produce hashes verificables
- Tokens JWT son válidos después de generación
- Rate limiting se aplica correctamente
- Audit logs son inmutables
- Y 52 propiedades más...

## Seguridad

### Mejores Prácticas Implementadas

- ✅ Hashing de contraseñas con bcrypt (cost factor 12)
- ✅ Tokens JWT con expiración corta (15 minutos)
- ✅ Refresh tokens con expiración larga (7 días)
- ✅ Blacklist de tokens para logout
- ✅ Rate limiting en endpoints sensibles
- ✅ Audit trail completo de eventos de seguridad
- ✅ Detección de brute force y abuso
- ✅ Mensajes de error genéricos (prevención de enumeración)
- ✅ Contraseñas PDF por header (no query params)
- ✅ Sin información personal en respuestas públicas
- ✅ Timezone-aware datetimes
- ✅ Validación de configuración al inicio

### Recomendaciones Adicionales

- Usa HTTPS en producción (configura certificado SSL/TLS)
- Configura firewall para limitar acceso a base de datos
- Monitorea logs de auditoría regularmente
- Actualiza dependencias periódicamente
- Revisa alertas de seguridad en `audit_log`
- Configura backup automático de base de datos
- Usa secretos seguros en producción (no valores de ejemplo)

## Monitoreo y Logs

### Logs de Aplicación

Los logs se escriben a stdout/stderr. En producción, redirige a un archivo:

```bash
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000 \
  --access-logfile access.log \
  --error-logfile error.log
```

### Audit Log

Todos los eventos de seguridad y operaciones críticas se registran en la tabla `audit_log`:

```sql
SELECT * FROM audit_log 
WHERE action = 'LOGIN_FAILED' 
  AND created_at > NOW() - INTERVAL '1 hour'
ORDER BY created_at DESC;
```

### Métricas de Seguridad

Consulta eventos de seguridad:

```sql
-- Intentos de login fallidos por IP
SELECT ip_address, COUNT(*) as attempts
FROM audit_log
WHERE action = 'LOGIN_FAILED'
  AND created_at > NOW() - INTERVAL '1 day'
GROUP BY ip_address
HAVING COUNT(*) > 5
ORDER BY attempts DESC;

-- Alertas de seguridad recientes
SELECT *
FROM audit_log
WHERE action = 'SECURITY_ALERT'
  AND created_at > NOW() - INTERVAL '7 days'
ORDER BY created_at DESC;
```

## Troubleshooting

### Error: "JWT_SECRET_KEY must be at least 32 characters"

**Solución**: Genera una clave segura:
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Copia el resultado a `JWT_SECRET_KEY` en `.env`.

### Error: "Database connection failed"

**Solución**: Verifica que:
- PostgreSQL está corriendo
- `DATABASE_URL` en `.env` es correcta
- Usuario tiene permisos en la base de datos
- Base de datos existe: `CREATE DATABASE taller_db;`

### Error: "Invalid token" en todos los requests

**Solución**: 
- Verifica que `JWT_SECRET_KEY` es la misma en todos los servidores
- Verifica que el token no ha expirado
- Verifica que el formato del header es: `Authorization: Bearer {token}`

### Tests fallan con "bcrypt is too slow"

**Solución**: En tests, usa `BCRYPT_COST_FACTOR=4` en `.env.test`:
```bash
cp .env.test.example .env.test
# Edita .env.test y configura BCRYPT_COST_FACTOR=4
```

### Rate limiting bloquea requests legítimos

**Solución**: Agrega IPs confiables a whitelist:
```
RATE_LIMIT_WHITELIST_IPS=127.0.0.1,::1,192.168.1.100
```

## Contribuir

1. Crea un branch para tu feature: `git checkout -b feature/mi-feature`
2. Haz commits con mensajes descriptivos
3. Ejecuta tests: `pytest`
4. Ejecuta linter: `flake8 app/`
5. Crea un Pull Request

## Licencia

[Especificar licencia del proyecto]

## Contacto

[Información de contacto del equipo]
