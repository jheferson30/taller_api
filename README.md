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

### Opción 1: Instalación con Docker (Recomendado)

La forma más rápida de levantar el sistema completo con todos los servicios.

#### Requisitos

- Docker 20.10+
- Docker Compose 2.0+

#### Pasos

1. **Clonar el repositorio**

```bash
git clone <url-del-repositorio>
cd taller_api
```

2. **Configurar variables de entorno**

```bash
cp .env.example .env
```

Edita `.env` y configura las variables mínimas requeridas:

```env
# Base de datos
DB_PASSWORD=tu_password_seguro

# JWT
JWT_SECRET_KEY=tu_clave_secreta_minimo_32_caracteres

# Azure Key Vault (opcional, para producción)
AZURE_KEY_VAULT_URL=https://tu-vault.vault.azure.net/
```

3. **Levantar todos los servicios**

```bash
docker-compose up -d
```

Esto iniciará:
- API (FastAPI) en `http://localhost:8000`
- PostgreSQL en `localhost:5432`
- Redis en `localhost:6379`
- Celery Worker para procesamiento asíncrono

4. **Verificar que los servicios están corriendo**

```bash
docker-compose ps
```

Deberías ver todos los servicios con estado `Up` y `healthy`.

5. **Ver logs**

```bash
# Todos los servicios
docker-compose logs -f

# Solo API
docker-compose logs -f api

# Solo Celery worker
docker-compose logs -f celery_worker
```

6. **Acceder a la documentación**

Abre tu navegador en `http://localhost:8000/docs`

#### Comandos útiles de Docker

```bash
# Detener todos los servicios
docker-compose down

# Detener y eliminar volúmenes (¡cuidado! elimina datos)
docker-compose down -v

# Reconstruir imágenes después de cambios en código
docker-compose build

# Reconstruir y reiniciar
docker-compose up -d --build

# Ver logs en tiempo real
docker-compose logs -f

# Ejecutar comando en contenedor
docker-compose exec api python scripts/migrate_passwords.py

# Acceder a shell del contenedor
docker-compose exec api bash

# Acceder a PostgreSQL
docker-compose exec db psql -U postgres -d taller_db
```

#### Ejecutar migraciones de base de datos

```bash
# Aplicar migraciones
docker-compose exec api alembic upgrade head

# Crear nueva migración
docker-compose exec api alembic revision --autogenerate -m "Descripción del cambio"

# Ver historial de migraciones
docker-compose exec api alembic history
```

#### Troubleshooting Docker

**Problema: Puerto 8000 ya está en uso**

```bash
# Cambiar puerto en docker-compose.yml
ports:
  - "8001:8000"  # Usar puerto 8001 en host
```

**Problema: Base de datos no está lista**

```bash
# Ver logs de PostgreSQL
docker-compose logs db

# Reiniciar servicio de base de datos
docker-compose restart db
```

**Problema: Cambios en código no se reflejan**

```bash
# Reconstruir imagen
docker-compose up -d --build api
```

### Opción 2: Instalación Manual (Desarrollo Local)

Para desarrollo local sin Docker.

#### Requisitos

- Python 3.9+
- PostgreSQL 12+
- Redis 6+ (opcional, para Celery)

#### Pasos

1. **Clonar el repositorio**

```bash
git clone <url-del-repositorio>
cd taller_api
```

2. **Crear entorno virtual**

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

3. **Instalar dependencias**

```bash
pip install -r requirements.txt
```

4. **Configurar variables de entorno**

Copia el archivo de ejemplo y ajusta los valores:

```bash
cp .env.example .env
```

Edita `.env` y configura las variables requeridas (ver sección Variables de Entorno más abajo).

5. **Configurar base de datos**

Crea la base de datos en PostgreSQL:

```sql
CREATE DATABASE taller_db;
```

Ejecuta la migración:

```bash
psql -U postgres -d taller_db -f db/migracion_jwt_auth_2026_03_28.sql
```

6. **Migrar contraseñas existentes (si aplica)**

Si tienes usuarios existentes con contraseñas SHA256:

```bash
python scripts/migrate_passwords.py
```

Este script:
- Lee contraseñas de la tabla `configuracion_seguridad`
- Crea usuarios en la tabla `users` con hash SHA256 temporal
- Marca usuarios como `is_migrated=False`
- En el primer login exitoso, la contraseña se migra automáticamente a bcrypt

7. **Iniciar el servidor**

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

La API estará disponible en `http://localhost:8000`

Documentación interactiva: `http://localhost:8000/docs`

8. **(Opcional) Iniciar Celery Worker**

Si necesitas procesamiento asíncrono (generación de PDFs):

```bash
# En otra terminal
celery -A app.tasks.celery_app worker --loglevel=info
```

## Configuración de Azure Key Vault

Azure Key Vault proporciona gestión segura de secretos en producción, eliminando la necesidad de almacenar contraseñas y claves en archivos `.env` en texto plano.

### ¿Cuándo usar Azure Key Vault?

- **Producción**: Recomendado para todos los entornos de producción
- **Staging**: Recomendado para entornos de staging/pre-producción
- **Desarrollo local**: Opcional, el sistema usa fallback a variables de entorno

### Requisitos previos

- Cuenta de Azure activa
- Azure CLI instalado: [Instalar Azure CLI](https://docs.microsoft.com/en-us/cli/azure/install-azure-cli)
- Permisos para crear recursos en Azure

### Paso 1: Crear Azure Key Vault

```bash
# Iniciar sesión en Azure
az login

# Crear grupo de recursos (si no existe)
az group create --name taller-rg --location eastus

# Crear Key Vault
az keyvault create \
  --name taller-vault \
  --resource-group taller-rg \
  --location eastus
```

**Nota**: El nombre del Key Vault debe ser único globalmente en Azure.

### Paso 2: Almacenar secretos en Key Vault

```bash
# Almacenar contraseña de administrador
az keyvault secret set \
  --vault-name taller-vault \
  --name "admin-password" \
  --value "TuContraseñaSegura123!"

# Almacenar contraseña para PDFs
az keyvault secret set \
  --vault-name taller-vault \
  --name "pdf-password" \
  --value "PDFPassword123!"

# Almacenar clave secreta JWT (generar una segura)
az keyvault secret set \
  --vault-name taller-vault \
  --name "jwt-secret-key" \
  --value "$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"

# Almacenar contraseña de base de datos
az keyvault secret set \
  --vault-name taller-vault \
  --name "database-password" \
  --value "TuPasswordDB123!"
```

### Paso 3: Configurar permisos de acceso

#### Opción A: Managed Identity (Recomendado para Azure App Service)

```bash
# Habilitar Managed Identity en tu App Service
az webapp identity assign \
  --name tu-app-service \
  --resource-group taller-rg

# Obtener el Object ID de la Managed Identity
IDENTITY_ID=$(az webapp identity show \
  --name tu-app-service \
  --resource-group taller-rg \
  --query principalId -o tsv)

# Otorgar permisos de lectura de secretos
az keyvault set-policy \
  --name taller-vault \
  --object-id $IDENTITY_ID \
  --secret-permissions get list
```

#### Opción B: Service Principal (Para servidores externos)

```bash
# Crear Service Principal
az ad sp create-for-rbac \
  --name taller-api-sp \
  --role reader \
  --scopes /subscriptions/{subscription-id}/resourceGroups/taller-rg

# Otorgar permisos al Service Principal
az keyvault set-policy \
  --name taller-vault \
  --spn {app-id-del-service-principal} \
  --secret-permissions get list
```

**Nota**: Guarda las credenciales del Service Principal (appId, password, tenant) de forma segura.

### Paso 4: Configurar variables de entorno

Edita tu archivo `.env` y agrega:

```env
# URL del Key Vault
AZURE_KEY_VAULT_URL=https://taller-vault.vault.azure.net/

# Solo si usas Service Principal (Opción B)
AZURE_CLIENT_ID=<app-id-del-service-principal>
AZURE_CLIENT_SECRET=<password-del-service-principal>
AZURE_TENANT_ID=<tenant-id>
```

**Nota**: Si usas Managed Identity (Opción A), solo necesitas `AZURE_KEY_VAULT_URL`.

### Paso 5: Verificar configuración

Inicia la aplicación y verifica que los secretos se recuperan correctamente:

```bash
uvicorn app.main:app --reload
```

Revisa los logs de inicio. Deberías ver mensajes indicando que los secretos se recuperaron desde Azure Key Vault.

### Mapeo de secretos

El sistema mapea automáticamente los secretos de Key Vault a las variables de entorno:

| Secreto en Key Vault | Variable de entorno (fallback) | Uso |
|----------------------|--------------------------------|-----|
| `admin-password` | `ADMIN_PASSWORD` | Operaciones del sistema (legacy) |
| `pdf-password` | `PDF_PASSWORD` | Generación de PDFs protegidos |
| `jwt-secret-key` | `JWT_SECRET_KEY` | Firma de tokens JWT |
| `database-password` | `DATABASE_PASSWORD` | Conexión a PostgreSQL |

### Modo de fallback (desarrollo local)

Si `AZURE_KEY_VAULT_URL` no está configurado, el sistema automáticamente usa variables de entorno del archivo `.env`:

```env
# Desarrollo local sin Key Vault
# AZURE_KEY_VAULT_URL=  # Comentado o vacío

# El sistema usará estas variables como fallback
ADMIN_PASSWORD=dev_password
PDF_PASSWORD=dev_password
JWT_SECRET_KEY=dev_secret_key_at_least_32_chars
```

### Mejores prácticas

1. **Nunca commits secretos**: No incluyas valores reales en `.env.example`
2. **Rotación de secretos**: Actualiza secretos periódicamente en Key Vault
3. **Auditoría**: Habilita logging de acceso a Key Vault para auditoría
4. **Principio de mínimo privilegio**: Otorga solo permisos `get` y `list`, no `set` o `delete`
5. **Separación de entornos**: Usa Key Vaults separados para dev, staging y producción

### Troubleshooting

#### Error: "DefaultAzureCredential failed to retrieve a token"

**Causa**: La aplicación no puede autenticarse con Azure.

**Solución**:
- Si usas Managed Identity, verifica que está habilitada en tu App Service
- Si usas Service Principal, verifica que `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET` y `AZURE_TENANT_ID` están configurados
- Ejecuta `az login` si estás en desarrollo local

#### Error: "Secret 'xxx' not found in Key Vault"

**Causa**: El secreto no existe en Key Vault o el nombre no coincide.

**Solución**:
- Verifica que el secreto existe: `az keyvault secret list --vault-name taller-vault`
- Verifica el nombre exacto (Key Vault usa guiones, no guiones bajos)
- Crea el secreto faltante con `az keyvault secret set`

#### Error: "Access denied to Key Vault"

**Causa**: La identidad no tiene permisos para leer secretos.

**Solución**:
- Verifica los permisos: `az keyvault show --name taller-vault`
- Otorga permisos con `az keyvault set-policy` (ver Paso 3)

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

### Azure Key Vault (Gestión de Secretos)

| Variable | Descripción | Valor por Defecto | Requerida |
|----------|-------------|-------------------|-----------|
| `AZURE_KEY_VAULT_URL` | URL del Azure Key Vault para gestión segura de secretos | - | ❌ |

**Formato**: `https://<vault-name>.vault.azure.net/`

**Nota**: Si no se configura, el sistema usará variables de entorno como fallback. Ver sección "Configuración de Azure Key Vault" para detalles de setup.

### CORS

| Variable | Descripción | Valor por Defecto | Requerida |
|----------|-------------|-------------------|-----------|
| `ALLOWED_ORIGINS` | Orígenes permitidos para CORS (separados por comas) | `*` | ❌ |

**Ejemplo**: `http://localhost:3000,http://localhost:5173,https://taller.com`

## Migraciones de Base de Datos con Alembic

El proyecto usa Alembic para gestionar cambios en el esquema de la base de datos de forma versionada y controlada.

### ¿Qué es Alembic?

Alembic es una herramienta de migraciones de base de datos para SQLAlchemy que permite:
- Versionar cambios en el esquema de la base de datos
- Aplicar y revertir cambios de forma controlada
- Generar migraciones automáticamente desde los modelos
- Mantener historial de cambios en el esquema

### Comandos Básicos

#### Ver estado actual de migraciones

```bash
# Ver historial de migraciones
alembic history

# Ver migración actual aplicada
alembic current

# Ver migraciones pendientes
alembic history --verbose
```

#### Aplicar migraciones

```bash
# Aplicar todas las migraciones pendientes
alembic upgrade head

# Aplicar una migración específica
alembic upgrade <revision_id>

# Aplicar siguiente migración
alembic upgrade +1
```

#### Revertir migraciones

```bash
# Revertir última migración
alembic downgrade -1

# Revertir a una migración específica
alembic downgrade <revision_id>

# Revertir todas las migraciones (¡cuidado!)
alembic downgrade base
```

#### Crear nuevas migraciones

```bash
# Generar migración automáticamente desde cambios en modelos
alembic revision --autogenerate -m "Descripción del cambio"

# Crear migración vacía (para editar manualmente)
alembic revision -m "Descripción del cambio"
```

### Workflow de Desarrollo

#### 1. Modificar modelos

Edita los archivos en `app/modelos/` para agregar, modificar o eliminar tablas/columnas:

```python
# app/modelos/ticket.py
class Ticket(Base):
    __tablename__ = "tickets"
    
    id = Column(Integer, primary_key=True)
    placa = Column(String(10), nullable=False)
    # Agregar nueva columna
    prioridad = Column(String(20), default="NORMAL")  # Nueva columna
```

#### 2. Generar migración

```bash
alembic revision --autogenerate -m "Add priority column to tickets"
```

Esto genera un archivo en `migrations/versions/` con el código de migración.

#### 3. Revisar migración generada

Abre el archivo generado y verifica que los cambios son correctos:

```python
# migrations/versions/xxxx_add_priority_column_to_tickets.py
def upgrade() -> None:
    op.add_column('tickets', sa.Column('prioridad', sa.String(20), nullable=True))

def downgrade() -> None:
    op.drop_column('tickets', 'prioridad')
```

**Importante**: Alembic no detecta todos los cambios automáticamente. Revisa siempre la migración generada.

#### 4. Aplicar migración

```bash
# En desarrollo
alembic upgrade head

# En producción (con Docker)
docker-compose exec api alembic upgrade head
```

#### 5. Verificar cambios

```bash
# Verificar que la migración se aplicó
alembic current

# Verificar en la base de datos
psql -U postgres -d taller_db -c "\d tickets"
```

### Workflow en Docker

Cuando usas Docker, ejecuta los comandos de Alembic dentro del contenedor:

```bash
# Aplicar migraciones
docker-compose exec api alembic upgrade head

# Ver historial
docker-compose exec api alembic history

# Generar nueva migración
docker-compose exec api alembic revision --autogenerate -m "Descripción"

# Revertir migración
docker-compose exec api alembic downgrade -1
```

### Mejores Prácticas

1. **Siempre revisa las migraciones autogeneradas**: Alembic puede no detectar todos los cambios o generar código incorrecto.

2. **Usa nombres descriptivos**: `alembic revision -m "Add email column to users"` es mejor que `alembic revision -m "Update users"`

3. **Una migración por cambio lógico**: No mezcles cambios no relacionados en una sola migración.

4. **Prueba las migraciones en desarrollo primero**: Aplica y revierte la migración varias veces para asegurar que funciona correctamente.

5. **Backup antes de aplicar en producción**: Siempre haz backup de la base de datos antes de aplicar migraciones en producción.

6. **No modifiques migraciones ya aplicadas**: Si una migración ya fue aplicada en producción, crea una nueva migración para corregir errores.

7. **Documenta cambios complejos**: Agrega comentarios en las migraciones para explicar cambios complejos.

### Cambios que Alembic NO detecta automáticamente

Alembic puede no detectar:
- Cambios en nombres de tablas (usa `op.rename_table()`)
- Cambios en nombres de columnas (usa `op.alter_column()`)
- Cambios en tipos de datos (puede requerir conversión manual)
- Cambios en constraints complejos
- Cambios en índices personalizados

Para estos casos, edita manualmente la migración generada.

### Ejemplo: Migración Manual

```python
def upgrade() -> None:
    # Renombrar tabla
    op.rename_table('old_table_name', 'new_table_name')
    
    # Renombrar columna
    op.alter_column('tickets', 'old_column', new_column_name='new_column')
    
    # Cambiar tipo de dato con conversión
    op.execute("ALTER TABLE tickets ALTER COLUMN precio TYPE DECIMAL(10,2) USING precio::DECIMAL")
    
    # Agregar índice
    op.create_index('idx_tickets_placa', 'tickets', ['placa'])
    
    # Agregar constraint
    op.create_check_constraint(
        'check_precio_positivo',
        'tickets',
        'precio > 0'
    )

def downgrade() -> None:
    op.drop_constraint('check_precio_positivo', 'tickets')
    op.drop_index('idx_tickets_placa')
    op.execute("ALTER TABLE tickets ALTER COLUMN precio TYPE INTEGER USING precio::INTEGER")
    op.alter_column('tickets', 'new_column', new_column_name='old_column')
    op.rename_table('new_table_name', 'old_table_name')
```

### Troubleshooting

#### Error: "Can't locate revision identified by 'xxxx'"

**Causa**: La base de datos no tiene la tabla `alembic_version` o está desincronizada.

**Solución**:
```bash
# Marcar la base de datos en una revisión específica (sin aplicar cambios)
alembic stamp head

# O marcar en una revisión específica
alembic stamp <revision_id>
```

#### Error: "Target database is not up to date"

**Causa**: Hay migraciones pendientes.

**Solución**:
```bash
alembic upgrade head
```

#### Error: "Multiple head revisions are present"

**Causa**: Hay múltiples ramas de migraciones.

**Solución**:
```bash
# Ver las ramas
alembic branches

# Fusionar ramas
alembic merge -m "Merge branches" <rev1> <rev2>
```

#### Revertir migración que falló

Si una migración falla a mitad de aplicación:

```bash
# Marcar la base de datos en la revisión anterior
alembic stamp <revision_anterior>

# Corregir la migración
# Editar el archivo de migración

# Aplicar nuevamente
alembic upgrade head
```

### Migración Inicial

El proyecto incluye una migración inicial baseline (`7643f7cc1e15_initial_schema.py`) que representa el esquema creado por `db/migracion_jwt_auth_2026_03_28.sql`.

Para bases de datos existentes:

```bash
# Marcar la base de datos como si tuviera la migración inicial aplicada
alembic stamp head
```

Esto permite que Alembic gestione cambios futuros sin intentar recrear el esquema existente.

## Proceso de Deployment

### Pre-Deployment Checklist

Antes de hacer deployment a producción, verifica:

- [ ] Todas las variables de entorno están configuradas en `.env`
- [ ] `JWT_SECRET_KEY` es una clave segura de al menos 32 caracteres
- [ ] Azure Key Vault está configurado y los secretos están almacenados (recomendado para producción)
- [ ] `AZURE_KEY_VAULT_URL` está configurado en `.env` (si usas Key Vault)
- [ ] Permisos de acceso a Key Vault están configurados correctamente
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

## Code Quality

### Linting y Formateo con Ruff

El proyecto usa [Ruff](https://docs.astral.sh/ruff/) como linter y formateador de código Python. Ruff es extremadamente rápido y combina las funcionalidades de múltiples herramientas (flake8, isort, pyupgrade, etc.).

#### Ejecutar Linter

```bash
# Verificar código sin hacer cambios
ruff check app/

# Auto-corregir problemas detectados
ruff check app/ --fix
```

#### Formatear Código

```bash
# Formatear todos los archivos Python
ruff format app/

# Verificar formato sin hacer cambios
ruff format app/ --check
```

#### Verificación Completa

```bash
# Ejecutar linter y formateador juntos
ruff check app/ --fix && ruff format app/
```

### Type Checking con mypy

El proyecto incluye type hints completos y usa mypy para verificación estática de tipos:

```bash
# Verificar tipos en todo el proyecto
mypy app/

# Verificar módulo específico
mypy app/servicios/

# Generar reporte HTML
mypy app/ --html-report mypy-report/
```

### Pre-commit Hooks

El proyecto está configurado con pre-commit hooks que ejecutan automáticamente Ruff y mypy antes de cada commit:

```bash
# Instalar hooks (solo una vez)
pre-commit install

# Ejecutar manualmente en todos los archivos
pre-commit run --all-files

# Los hooks se ejecutan automáticamente en cada commit
git commit -m "mensaje"
```

Los hooks verifican:
- ✅ Formato de código con Ruff
- ✅ Calidad de código con Ruff linter
- ✅ Errores de tipo con mypy (opcional)

### Configuración

La configuración de Ruff y mypy está en `pyproject.toml`:

```toml
[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "W", "F", "I", "B", "C4", "UP", "ARG", "SIM"]

[tool.mypy]
python_version = "3.11"
check_untyped_defs = true
```

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

---

## Despliegue en Azure VM

Guía paso a paso para desplegar el sistema en una máquina virtual de Azure.

### Requisitos Previos

- Cuenta de Azure (suscripción de estudiante o paga)
- Azure CLI instalado (opcional, se puede usar Cloud Shell)
- Git instalado en la VM

### 1. Crear la VM en Azure

1. Ve a [portal.azure.com](https://portal.azure.com)
2. Crea una VM con:
   - **Imagen**: Ubuntu Server 24.04 LTS
   - **Tamaño**: Standard_B2s (recomendado para demo) o Standard_D2s_v3
   - **Región**: mexicocentral, canadacentral u otra disponible para tu suscripción
   - **Autenticación**: Clave SSH pública
3. Abre los puertos: **22** (SSH), **80** (HTTP), **443** (HTTPS), **8000** (API)

### 2. Conectarse a la VM

```bash
ssh -i ruta/a/tu-llave.pem azureuser@IP_PUBLICA_VM
```

### 3. Instalar Dependencias del Sistema

```bash
sudo apt update && sudo apt install -y python3 python3-pip python3-venv git nginx nodejs npm postgresql postgresql-contrib redis-server
sudo systemctl enable postgresql redis-server
sudo systemctl start postgresql redis-server
```

### 4. Configurar PostgreSQL

```bash
# Cambiar método de autenticación local
sudo sed -i 's/local   all             postgres                                peer/local   all             postgres                                trust/' /etc/postgresql/16/main/pg_hba.conf
sudo sed -i '/^host.*all.*all.*127.0.0.1/s/scram-sha-256/md5/' /etc/postgresql/16/main/pg_hba.conf
sudo systemctl restart postgresql

# Crear base de datos y usuario
sudo -u postgres psql -c "ALTER USER postgres WITH PASSWORD 'tu_password_seguro';"
sudo -u postgres psql -c "CREATE DATABASE taller_db;"

# Restaurar autenticación segura
sudo sed -i 's/local   all             postgres                                trust/local   all             postgres                                md5/' /etc/postgresql/16/main/pg_hba.conf
sudo systemctl restart postgresql
```

### 5. Clonar el Repositorio

```bash
git clone https://TOKEN@github.com/jheferson30/taller_api.git
cd taller_api
```

> **Nota**: Reemplaza `TOKEN` con un Personal Access Token de GitHub (Settings → Developer settings → Personal access tokens).

### 6. Configurar Entorno Virtual e Instalar Dependencias

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install "pydantic[email]"
```

### 7. Configurar Variables de Entorno

```bash
cp .env.example .env
```

Edita `.env` con los valores correctos:

```bash
# Valores mínimos requeridos
DATABASE_URL=postgresql+psycopg2://postgres:tu_password@127.0.0.1:5432/taller_db?client_encoding=utf8
JWT_SECRET_KEY=  # Generar con: python3 -c "import secrets; print(secrets.token_urlsafe(32))"
CSRF_SECRET_KEY= # Generar con: python3 -c "import secrets; print(secrets.token_urlsafe(32))"
ENVIRONMENT=development
ALLOWED_ORIGINS=http://IP_PUBLICA_VM:8000
ALLOWED_HOSTS=IP_PUBLICA_VM
ADMIN_PASSWORD=mecaapp123
PDF_PASSWORD=mecaapp123
AZURE_KEY_VAULT_URL=  # Dejar vacío si no usas Key Vault
PUBLIC_IP=IP_PUBLICA_VM  # Para que el QR de la app móvil muestre la IP correcta
```

### 8. Ejecutar Migraciones

```bash
alembic upgrade head
```

### 9. Crear Usuario Admin Inicial

```bash
python scripts/seed_admin.py
```

Esto crea el usuario `admin` con contraseña `Admin1234!` si no existe.

> **⚠️ IMPORTANTE**: Cambia la contraseña después del primer login.

Puedes personalizar las credenciales con variables de entorno:

```bash
ADMIN_USERNAME=admin ADMIN_PASSWORD=MiPasswordSeguro123! python scripts/seed_admin.py
```

### 10. Compilar el Frontend

```bash
cd frontend
npm install
chmod +x node_modules/.bin/vite
npm run build
cd ..
```

### 11. Configurar Servicio Systemd (Arranque Automático)

```bash
sudo tee /etc/systemd/system/taller.service << 'EOF'
[Unit]
Description=Taller API
After=network.target

[Service]
User=azureuser
WorkingDirectory=/home/azureuser/taller_api
Environment="PATH=/home/azureuser/taller_api/venv/bin"
ExecStart=/home/azureuser/taller_api/venv/bin/gunicorn -w 2 -k uvicorn.workers.UvicornWorker app.main:app --bind 0.0.0.0:8000
Restart=always

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl enable taller
sudo systemctl start taller
```

La app ahora:
- ✅ Arranca automáticamente cuando la VM se enciende
- ✅ Se reinicia sola si falla
- ✅ Se apaga cuando apagas la VM

### 12. Verificar que Funciona

```bash
sudo systemctl status taller
curl http://localhost:8000
```

Abre en el navegador: `http://IP_PUBLICA_VM:8000`

---

### Actualizar el Código en la VM

Cuando hagas cambios en el código y los subas a GitHub:

```bash
cd ~/taller_api
git fetch origin && git reset --hard origin/main
source venv/bin/activate
pip install -r requirements.txt
cd frontend && chmod +x node_modules/.bin/vite && npm run build && cd ..
sudo systemctl restart taller
```

### Conectarse a la VM

```bash
ssh -i ruta/a/tu-llave.pem azureuser@IP_PUBLICA_VM
```

Si perdiste la llave SSH, genera una nueva desde tu PC:

```bash
ssh-keygen -t ed25519 -f ~/Downloads/nueva-llave
```

Y agrega la llave pública a la VM desde Azure Portal → VM → Operaciones → Ejecutar comando → RunShellScript:

```bash
echo "CONTENIDO_DE_nueva-llave.pub" >> /home/azureuser/.ssh/authorized_keys
```

### Apagar/Encender la VM para Ahorrar Crédito

```bash
# Apagar (deallocate para no cobrar)
az vm deallocate --resource-group mecaapp-rg --name mecaapp-vm

# Encender
az vm start --resource-group mecaapp-rg --name mecaapp-vm
```

> **Nota**: La IP pública puede cambiar al reiniciar la VM si no tienes IP estática. Actualiza `PUBLIC_IP` en el `.env` si cambia.
