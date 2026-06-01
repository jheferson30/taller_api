# Diseño Técnico: Super Admin — Gestión de Talleres

## Introducción

Este documento describe el diseño técnico para implementar el panel de administración del SUPER_ADMIN. Construye sobre la arquitectura multi-tenant existente (`multi-tenant-taller-id`) y extiende los modelos, servicios y rutas ya implementados.

---

## 1. Cambios en Modelos SQLAlchemy

### 1.1 Modelo `Taller` — `app/modelos/taller.py`

Agregar campos de ciclo de vida, bloqueo de emergencia y estado:

```python
from sqlalchemy import Boolean, Column, DateTime, Enum, Integer, String
import enum

class EstadoTaller(enum.StrEnum):
    TRIAL = "TRIAL"
    ACTIVO = "ACTIVO"
    SUSPENDIDO = "SUSPENDIDO"
    CANCELADO = "CANCELADO"

class Taller(Base):
    __tablename__ = "talleres"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(200), unique=True, nullable=False, index=True)
    nit = Column(String(50), nullable=True)
    direccion = Column(String(300), nullable=True)
    telefono = Column(String(50), nullable=True)
    activo = Column(Boolean, default=True, nullable=False, index=True)

    # Ciclo de vida
    estado = Column(Enum(EstadoTaller), default=EstadoTaller.TRIAL, nullable=False, index=True)
    fecha_inicio_trial = Column(DateTime(timezone=True), nullable=True)
    dias_trial = Column(Integer, nullable=True)
    fecha_suspension = Column(DateTime(timezone=True), nullable=True)
    fecha_cancelacion = Column(DateTime(timezone=True), nullable=True)

    # Bloqueo de emergencia
    bloqueado_emergencia = Column(Boolean, default=False, nullable=False)
    fecha_bloqueo_emergencia = Column(DateTime(timezone=True), nullable=True)
    motivo_bloqueo_emergencia = Column(String(500), nullable=True)

    fecha_creacion = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    fecha_actualizacion = Column(DateTime(timezone=True), onupdate=func.now())

    # Relaciones
    configuracion = relationship("ConfiguracionTaller", back_populates="taller", uselist=False)
    usuarios = relationship("User", back_populates="taller")
```

### 1.2 Modelo `User` — `app/modelos/user.py`

Hacer `taller_id` nullable para soportar SUPER_ADMIN:

```python
# Cambiar de:
taller_id = Column(Integer, ForeignKey("talleres.id"), nullable=False, index=True)
# A:
taller_id = Column(Integer, ForeignKey("talleres.id"), nullable=True, index=True)
```

### 1.3 Modelo `ConfiguracionTaller` — `app/modelos/configuracion_taller.py`

Agregar campos de localización:

```python
# Campos nuevos a agregar
moneda = Column(String(3), nullable=False, default="COP")   # ISO 4217
idioma = Column(String(2), nullable=False, default="es")    # ISO 639-1
timezone = Column(String(100), nullable=False, default="America/Bogota")  # IANA
```

### 1.4 Enum `AuditAction` — `app/modelos/audit_log.py`

Agregar nuevas acciones:

```python
TALLER_ACTIVATE = "TALLER_ACTIVATE"
TALLER_SUSPEND = "TALLER_SUSPEND"
TALLER_CANCEL = "TALLER_CANCEL"
TALLER_EMERGENCY_BLOCK = "TALLER_EMERGENCY_BLOCK"
TALLER_EMERGENCY_UNBLOCK = "TALLER_EMERGENCY_UNBLOCK"
PASSWORD_RESET_FORCED = "PASSWORD_RESET_FORCED"
PASSWORD_RESET_MASS = "PASSWORD_RESET_MASS"
```

---

## 2. Cambios en AuthMiddleware

### `app/seguridad/auth_middleware.py`

Tres cambios clave:

**a) Permitir `taller_id = NULL` para SUPER_ADMIN:**

```python
# Verificar que el taller del usuario esté activo
# SUPER_ADMIN tiene taller_id = None — omitir verificación
user_roles = [role.name for role in user.roles] if user.roles else []
is_super_admin = "SUPER_ADMIN" in user_roles

if not is_super_admin and user.taller_id:
    from app.modelos.taller import Taller, EstadoTaller
    taller = db.query(Taller).filter(Taller.id == user.taller_id).first()
    
    if not taller:
        return JSONResponse(status_code=403, content={"detail": "Taller no encontrado"})
    
    # Verificar bloqueo de emergencia (tiene prioridad sobre estado)
    if taller.bloqueado_emergencia:
        return JSONResponse(
            status_code=403,
            content={"detail": "Taller bloqueado por razones de seguridad. Contacte al administrador de la plataforma."}
        )
    
    # Verificar estado del taller
    if taller.estado in (EstadoTaller.SUSPENDIDO, EstadoTaller.CANCELADO):
        return JSONResponse(
            status_code=403,
            content={"detail": "Taller suspendido. Contacte al administrador de la plataforma."}
        )
```

**b) Inyectar `is_super_admin` en `request.state`:**

```python
request.state.user = user
request.state.taller_id = payload.get("taller_id")  # None para SUPER_ADMIN
request.state.is_super_admin = is_super_admin
```

---

## 3. Nuevos Esquemas Pydantic

### `app/esquemas/taller_schema.py` — Extender con nuevos campos

```python
from enum import StrEnum

class EstadoTallerEnum(StrEnum):
    TRIAL = "TRIAL"
    ACTIVO = "ACTIVO"
    SUSPENDIDO = "SUSPENDIDO"
    CANCELADO = "CANCELADO"

class TallerCreate(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=200)
    nit: str | None = Field(None, max_length=50)
    direccion: str | None = Field(None, max_length=300)
    telefono: str | None = Field(None, max_length=50)
    dias_trial: int = Field(default=30, ge=1, le=365)

class TallerUpdate(BaseModel):
    nombre: str | None = Field(None, min_length=1, max_length=200)
    nit: str | None = None
    direccion: str | None = None
    telefono: str | None = None
    activo: bool | None = None
    estado: EstadoTallerEnum | None = None
    dias_trial: int | None = Field(None, ge=1, le=365)

class TallerResponse(BaseModel):
    id: int
    nombre: str
    nit: str | None = None
    direccion: str | None = None
    telefono: str | None = None
    activo: bool
    estado: str
    fecha_creacion: datetime
    fecha_inicio_trial: datetime | None = None
    dias_trial: int | None = None
    dias_restantes_trial: int | None = None  # calculado
    bloqueado_emergencia: bool
    fecha_bloqueo_emergencia: datetime | None = None

    class Config:
        from_attributes = True

class TallerMetricasResponse(BaseModel):
    taller_id: int
    usuarios_activos: int
    tickets_historicos: int
    tickets_mes_actual: int
    fecha_ultimo_acceso: datetime | None = None

class MetricasGlobalesResponse(BaseModel):
    total_talleres: int
    talleres_por_estado: dict[str, int]
    total_usuarios_activos: int
    total_usuarios: int

class TallerRecursosResponse(BaseModel):
    taller_id: int
    almacenamiento_bytes: int
    almacenamiento_mb: float
    tickets_mes_actual: int
    limite_tickets_mes: int | None = None

class BloqueoEmergenciaRequest(BaseModel):
    motivo: str = Field(..., min_length=10, max_length=500)

class CrearAdminTallerRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8)
    nombre_completo: str | None = None
```

---

## 4. Extensión del `TallerService`

### `app/servicios/taller_service.py`

Agregar métodos nuevos al servicio existente:

```python
def cambiar_estado(self, taller_id: int, nuevo_estado: EstadoTaller,
                   updated_by: int, ip_address: str, user_agent: str) -> Taller:
    """Cambia el estado del taller con validaciones y audit log."""

def activar_bloqueo_emergencia(self, taller_id: int, motivo: str,
                                updated_by: int, ip_address: str, user_agent: str) -> Taller:
    """Bloqueo inmediato + invalida todos los tokens del taller."""

def levantar_bloqueo_emergencia(self, taller_id: int,
                                 updated_by: int, ip_address: str, user_agent: str) -> Taller:
    """Levanta el bloqueo de emergencia."""

def obtener_metricas(self, taller_id: int) -> dict:
    """Retorna métricas operativas del taller (solo conteos)."""

def obtener_metricas_globales(self) -> dict:
    """Retorna métricas agregadas de toda la plataforma."""

def obtener_recursos(self, taller_id: int) -> dict:
    """Calcula almacenamiento usado y tickets del mes."""

def crear_admin_taller(self, taller_id: int, username: str, email: str,
                        password: str, nombre_completo: str | None,
                        created_by: int, ip_address: str, user_agent: str) -> User:
    """Crea el primer ADMIN de un taller. Solo SUPER_ADMIN."""

def forzar_reset_password(self, taller_id: int, usuario_id: int,
                           updated_by: int, ip_address: str, user_agent: str) -> str:
    """Invalida tokens y genera token de reset de un solo uso (24h)."""

def forzar_reset_password_masivo(self, taller_id: int,
                                  updated_by: int, ip_address: str, user_agent: str) -> int:
    """Reset masivo de todos los usuarios del taller. Retorna cantidad afectada."""

def obtener_intentos_fallidos(self, taller_id: int, desde: datetime | None,
                               page: int, page_size: int) -> list:
    """Retorna intentos de login fallidos del taller desde Audit_Log."""

def obtener_auditoria_global(self, taller_id: int | None, user_id: int | None,
                              accion: str | None, desde: datetime | None,
                              hasta: datetime | None, page: int, page_size: int) -> list:
    """Auditoría cruzada global con filtros."""
```

---

## 5. Extensión del `TallerRepository`

### `app/repositorios/taller_repository.py`

Agregar métodos de consulta para métricas:

```python
def get_metricas(self, taller_id: int) -> dict:
    """Conteos operativos del taller en una sola query."""
    from sqlalchemy import func
    from app.modelos.ticket import Ticket
    from app.modelos.user import User
    from datetime import datetime, timezone

    ahora = datetime.now(timezone.utc)
    inicio_mes = ahora.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    usuarios_activos = (
        self.db.query(func.count(User.id))
        .filter(User.taller_id == taller_id, User.is_active == True)
        .scalar()
    )
    tickets_historicos = (
        self.db.query(func.count(Ticket.id))
        .filter(Ticket.taller_id == taller_id)
        .scalar()
    )
    tickets_mes = (
        self.db.query(func.count(Ticket.id))
        .filter(Ticket.taller_id == taller_id, Ticket.fecha_ingreso >= inicio_mes)
        .scalar()
    )
    return {
        "usuarios_activos": usuarios_activos or 0,
        "tickets_historicos": tickets_historicos or 0,
        "tickets_mes_actual": tickets_mes or 0,
    }

def get_metricas_globales(self) -> dict:
    """Métricas agregadas de toda la plataforma."""
    from sqlalchemy import func
    from app.modelos.user import User

    total = self.db.query(func.count(Taller.id)).scalar()
    por_estado = (
        self.db.query(Taller.estado, func.count(Taller.id))
        .group_by(Taller.estado)
        .all()
    )
    usuarios_activos = (
        self.db.query(func.count(User.id))
        .filter(User.is_active == True)
        .scalar()
    )
    total_usuarios = self.db.query(func.count(User.id)).scalar()

    return {
        "total_talleres": total or 0,
        "talleres_por_estado": {estado: count for estado, count in por_estado},
        "total_usuarios_activos": usuarios_activos or 0,
        "total_usuarios": total_usuarios or 0,
    }
```

---

## 6. Nuevas Rutas

### `app/rutas/super_admin_ruta.py` — Router dedicado con prefijo `/super-admin`

Todas las rutas del SUPER_ADMIN van bajo el prefijo `/super-admin/`. Nunca mezclar con rutas de taller operativas.

```
# Gestión de talleres
GET    /super-admin/talleres                                      → listar todos los talleres
POST   /super-admin/talleres                                      → crear taller
GET    /super-admin/talleres/{taller_id}                          → detalle del taller
PATCH  /super-admin/talleres/{taller_id}                          → actualizar datos
PATCH  /super-admin/talleres/{taller_id}/estado                   → cambiar estado (TRIAL→ACTIVO→SUSPENDIDO→CANCELADO)

# Onboarding
POST   /super-admin/talleres/{taller_id}/usuarios                 → crear primer ADMIN del taller
POST   /super-admin/talleres/{taller_id}/logo                     → subir logo (uploads/talleres/{id}/logos/)

# Métricas
GET    /super-admin/talleres/{taller_id}/metricas                 → métricas del taller
GET    /super-admin/metricas/global                               → métricas globales de la plataforma

# Recursos
GET    /super-admin/talleres/{taller_id}/recursos                 → almacenamiento y tickets vs límite

# Gestión de usuarios
POST   /super-admin/talleres/{taller_id}/usuarios/{uid}/reset-password   → reset individual
POST   /super-admin/talleres/{taller_id}/reset-passwords                 → reset masivo

# Bloqueo de emergencia
POST   /super-admin/talleres/{taller_id}/bloqueo-emergencia              → activar bloqueo
DELETE /super-admin/talleres/{taller_id}/bloqueo-emergencia              → levantar bloqueo

# Seguridad
GET    /super-admin/talleres/{taller_id}/seguridad/intentos-fallidos     → login fallidos

# Auditoría global
GET    /super-admin/auditoria                                     → audit log cruzado con filtros

# Comunicación
POST   /super-admin/talleres/{taller_id}/notificaciones           → enviar notificación a un taller
POST   /super-admin/notificaciones                                → enviar notificación global
GET    /super-admin/notificaciones                                → historial de notificaciones
```

Todos protegidos con `@require_auth` + `@require_role("SUPER_ADMIN")`.

```python
# app/rutas/super_admin_ruta.py
router = APIRouter(prefix="/super-admin", tags=["Super Admin"])
```

---

## 7. Script SQL del SUPER_ADMIN

### `scripts/crear_super_admin.sql`

```sql
-- ============================================================================
-- SCRIPT DE CREACIÓN DEL SUPER_ADMIN
-- ============================================================================
-- PROPÓSITO: Crear el usuario administrador de la plataforma SaaS.
--
-- ADVERTENCIA: Este es el ÚNICO método autorizado para crear un SUPER_ADMIN.
--              NUNCA exponer un endpoint HTTP para este propósito.
--
-- INSTRUCCIONES:
--   1. Cambiar 'CAMBIAR_ESTA_CONTRASENA' por una contraseña segura
--   2. Ejecutar: psql -U postgres -d taller_v3 -f scripts/crear_super_admin.sql
--   3. Guardar la contraseña en un gestor de contraseñas seguro
-- ============================================================================

-- El hash debe generarse con Python antes de ejecutar:
-- python -c "from passlib.context import CryptContext; ctx = CryptContext(schemes=['bcrypt']); print(ctx.hash('TU_CONTRASENA_AQUI'))"

DO $$
DECLARE
    v_role_id INTEGER;
    v_user_id INTEGER;
    v_password_hash TEXT := '$2b$12$REEMPLAZAR_CON_HASH_BCRYPT_REAL';
BEGIN
    -- 1. Asegurar que el rol SUPER_ADMIN existe
    INSERT INTO roles (name, description)
    VALUES ('SUPER_ADMIN', 'Administrador de la plataforma SaaS. Sin afiliación a ningún taller.')
    ON CONFLICT (name) DO NOTHING;

    SELECT id INTO v_role_id FROM roles WHERE name = 'SUPER_ADMIN';

    -- 2. Crear o actualizar el usuario SUPER_ADMIN
    INSERT INTO users (taller_id, username, email, password_hash, is_active, is_migrated)
    VALUES (NULL, 'superadmin', 'admin@plataforma.com', v_password_hash, TRUE, TRUE)
    ON CONFLICT (username) DO UPDATE
        SET password_hash = EXCLUDED.password_hash,
            is_active = TRUE;

    SELECT id INTO v_user_id FROM users WHERE username = 'superadmin';

    -- 3. Asignar rol SUPER_ADMIN
    INSERT INTO user_roles (user_id, role_id)
    VALUES (v_user_id, v_role_id)
    ON CONFLICT (user_id, role_id) DO NOTHING;

    RAISE NOTICE '✅ SUPER_ADMIN creado/actualizado exitosamente (user_id: %)', v_user_id;
    RAISE NOTICE '   Username: superadmin';
    RAISE NOTICE '   IMPORTANTE: Cambia la contraseña por defecto inmediatamente.';
END $$;
```

---

## 8. Migración Alembic

### `migrations/versions/b2c3d4e5f6a7_super_admin_fields.py`

```python
"""Add super admin fields to talleres and users

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
"""

def upgrade():
    # Hacer taller_id nullable en users (para SUPER_ADMIN)
    op.alter_column('users', 'taller_id', nullable=True)

    # Agregar campos de ciclo de vida a talleres
    op.execute("CREATE TYPE estadotaller AS ENUM ('TRIAL', 'ACTIVO', 'SUSPENDIDO', 'CANCELADO')")
    op.add_column('talleres', sa.Column('estado', sa.Enum('TRIAL', 'ACTIVO', 'SUSPENDIDO', 'CANCELADO', name='estadotaller'), nullable=False, server_default='TRIAL'))
    op.add_column('talleres', sa.Column('fecha_inicio_trial', sa.DateTime(timezone=True), nullable=True))
    op.add_column('talleres', sa.Column('dias_trial', sa.Integer(), nullable=True))
    op.add_column('talleres', sa.Column('fecha_suspension', sa.DateTime(timezone=True), nullable=True))
    op.add_column('talleres', sa.Column('fecha_cancelacion', sa.DateTime(timezone=True), nullable=True))

    # Agregar campos de bloqueo de emergencia
    op.add_column('talleres', sa.Column('bloqueado_emergencia', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('talleres', sa.Column('fecha_bloqueo_emergencia', sa.DateTime(timezone=True), nullable=True))
    op.add_column('talleres', sa.Column('motivo_bloqueo_emergencia', sa.String(500), nullable=True))

    # Agregar campos de localización a configuracion_taller
    op.add_column('configuracion_taller', sa.Column('moneda', sa.String(3), nullable=False, server_default='COP'))
    op.add_column('configuracion_taller', sa.Column('idioma', sa.String(2), nullable=False, server_default='es'))
    op.add_column('configuracion_taller', sa.Column('timezone', sa.String(100), nullable=False, server_default='America/Bogota'))

    # Índice en estado del taller
    op.create_index('ix_talleres_estado', 'talleres', ['estado'])

def downgrade():
    op.drop_index('ix_talleres_estado', table_name='talleres')
    op.drop_column('configuracion_taller', 'timezone')
    op.drop_column('configuracion_taller', 'idioma')
    op.drop_column('configuracion_taller', 'moneda')
    op.drop_column('talleres', 'motivo_bloqueo_emergencia')
    op.drop_column('talleres', 'fecha_bloqueo_emergencia')
    op.drop_column('talleres', 'bloqueado_emergencia')
    op.drop_column('talleres', 'fecha_cancelacion')
    op.drop_column('talleres', 'fecha_suspension')
    op.drop_column('talleres', 'dias_trial')
    op.drop_column('talleres', 'fecha_inicio_trial')
    op.drop_column('talleres', 'estado')
    op.execute("DROP TYPE estadotaller")
    op.alter_column('users', 'taller_id', nullable=False)
```

---

## 9. Organización de Uploads por Taller

### `app/utils/upload_utils.py` — Función centralizada de rutas

Estructura de directorios según el steering `arquitectura-multitenant.md`:

```
uploads/talleres/{taller_id}/logos/
uploads/talleres/{taller_id}/fotos/
uploads/talleres/{taller_id}/exports/
uploads/talleres/{taller_id}/pdfs/
uploads/talleres/{taller_id}/compras/
uploads/talleres/{taller_id}/firmas/
```

```python
def get_upload_path(taller_id: int, tipo: str) -> str:
    """
    Retorna la ruta de almacenamiento para un archivo del taller.
    Crea el directorio si no existe.
    
    Tipos válidos: logos, fotos, exports, pdfs, compras, firmas
    """
    import os
    path = os.path.join("uploads", "talleres", str(taller_id), tipo)
    os.makedirs(path, exist_ok=True)
    return path
```

Todos los endpoints de upload deben usar `get_upload_path(request.state.taller_id, tipo)`. El `taller_id` siempre viene de `request.state`, nunca del body.

---

## 10. Propiedades de Corrección (PBT)

### Propiedades a verificar con tests:

**P_SA1 — SUPER_ADMIN sin taller:**
El JWT del SUPER_ADMIN tiene `taller_id = null`. El AuthMiddleware no rechaza el request por falta de taller.

**P_SA2 — Bloqueo de emergencia tiene prioridad:**
Si `bloqueado_emergencia = true`, el acceso es rechazado independientemente del `estado` del taller.

**P_SA3 — Estado SUSPENDIDO bloquea acceso:**
Si `estado = SUSPENDIDO` o `CANCELADO`, todos los requests de usuarios del taller retornan HTTP 403.

**P_SA4 — Métricas sin datos privados:**
`GET /talleres/{id}/metricas` retorna solo conteos enteros, nunca strings con nombres o contenido de tickets.

**P_SA5 — Reset masivo invalida todos los tokens:**
Después de `POST /talleres/{id}/reset-passwords`, ningún token JWT previo de usuarios del taller es válido.

**P_SA6 — Uploads aislados por taller:**
Un archivo subido por el taller A nunca se almacena en la carpeta del taller B.

---

## 11. Resumen de Archivos Afectados

| Acción | Archivos |
|--------|---------|
| **Modificar modelos** | `app/modelos/taller.py`, `app/modelos/user.py`, `app/modelos/configuracion_taller.py`, `app/modelos/audit_log.py` |
| **Modificar seguridad** | `app/seguridad/auth_middleware.py` |
| **Modificar servicios** | `app/servicios/taller_service.py` |
| **Modificar repositorios** | `app/repositorios/taller_repository.py` |
| **Modificar rutas** | `app/rutas/taller_ruta.py`, `app/rutas/upload_ruta.py` |
| **Modificar esquemas** | `app/esquemas/taller_schema.py` |
| **Crear nuevos** | `scripts/crear_super_admin.sql` |
| **Crear migración** | `migrations/versions/b2c3d4e5f6a7_super_admin_fields.py` |
| **Agregar router** | `app/rutas/taller_ruta.py` (nuevos endpoints), `app/main.py` (router `/admin`) |
