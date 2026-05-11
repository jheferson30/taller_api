# Diseño Técnico: Multi-Tenant con taller_id

## Introducción

Este documento describe el diseño técnico para implementar el sistema multi-tenant en la aplicación de gestión de taller mecánico. La estrategia elegida es **discriminador de columna por tabla** (`taller_id` en cada tabla), que es el enfoque más simple, performante y compatible con el esquema PostgreSQL existente.

---

## 1. Arquitectura General

```
┌─────────────────────────────────────────────────────────┐
│                     HTTP Request                        │
└─────────────────────┬───────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────┐
│              AuthMiddleware (existente)                  │
│  + Valida JWT                                           │
│  + Inyecta request.state.user                           │
│  + Inyecta request.state.taller_id  ← NUEVO             │
│  + Verifica taller.activo == True   ← NUEVO             │
└─────────────────────┬───────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────┐
│                   Rutas / Endpoints                      │
│  Extraen taller_id de request.state (nunca del body)    │
└─────────────────────┬───────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────┐
│                    Servicios                             │
│  Reciben taller_id como parámetro explícito             │
│  Verifican integridad referencial cross-tenant          │
└─────────────────────┬───────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────┐
│              TenantRepository (NUEVO)                    │
│  Clase base que aplica filtro taller_id automáticamente │
│  en todas las operaciones CRUD                          │
└─────────────────────┬───────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────┐
│                  PostgreSQL                              │
│  Todas las tablas operativas tienen columna taller_id   │
│  Índices compuestos (taller_id, campo_principal)        │
└─────────────────────────────────────────────────────────┘
```

---

## 2. Nuevo Modelo: Taller

### Archivo: `app/modelos/taller.py`

```python
from sqlalchemy import Boolean, Column, DateTime, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.configuracion.base_datos import Base


class Taller(Base):
    __tablename__ = "talleres"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(200), unique=True, nullable=False, index=True)
    nit = Column(String(50), nullable=True)
    direccion = Column(String(300), nullable=True)
    telefono = Column(String(50), nullable=True)
    activo = Column(Boolean, default=True, nullable=False, index=True)
    fecha_creacion = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    fecha_actualizacion = Column(DateTime(timezone=True), onupdate=func.now())

    # Relaciones
    configuracion = relationship("ConfiguracionTaller", back_populates="taller", uselist=False)
    usuarios = relationship("User", back_populates="taller")
```

---

## 3. Cambios en Modelos Existentes

### 3.1 User — `app/modelos/user.py`

Agregar columna `taller_id` y relación:

```python
from sqlalchemy import ForeignKey
# ...
taller_id = Column(Integer, ForeignKey("talleres.id"), nullable=False, index=True)
# Relación
taller = relationship("Taller", back_populates="usuarios")
```

### 3.2 Tablas operativas — columna a agregar en cada modelo

Todas las siguientes tablas reciben exactamente esta columna:

```python
taller_id = Column(Integer, ForeignKey("talleres.id"), nullable=False, index=True)
```

| Modelo | Archivo |
|--------|---------|
| `Ticket` | `app/modelos/ticket.py` |
| `Vehiculo` | `app/modelos/vehiculo.py` |
| `Cita` | `app/modelos/cita.py` |
| `MovimientoCaja` | `app/modelos/movimiento_caja.py` |
| `Mecanico` | `app/modelos/mecanico.py` |
| `TicketRepuesto` | `app/modelos/ticket_repuesto.py` |
| `TicketProceso` | `app/modelos/ticket_proceso.py` |
| `TicketCobro` | `app/modelos/ticket_cobro.py` |
| `TicketCompra` | `app/modelos/ticket_compra.py` |
| `TicketFoto` | `app/modelos/ticket_foto.py` |
| `CambioMovimientoCaja` | `app/modelos/cambio_movimiento_caja.py` |
| `LogNotificacion` | `app/modelos/log_notificacion.py` |

### 3.3 ConfiguracionTaller — `app/modelos/configuracion_taller.py`

Agregar relación 1:1 con Taller:

```python
taller_id = Column(Integer, ForeignKey("talleres.id"), unique=True, nullable=False, index=True)
taller = relationship("Taller", back_populates="configuracion")
```

### 3.4 AuditLog — `app/modelos/audit_log.py`

Agregar columna nullable (el audit log puede existir antes de que haya contexto de taller):

```python
taller_id = Column(Integer, ForeignKey("talleres.id", ondelete="SET NULL"), nullable=True, index=True)
```

Agregar nuevas acciones al enum `AuditAction`:

```python
TALLER_CREATE = "TALLER_CREATE"
TALLER_UPDATE = "TALLER_UPDATE"
TALLER_DEACTIVATE = "TALLER_DEACTIVATE"
```

---

## 4. Cambios en Índices Únicos

Los índices únicos globales deben convertirse en únicos por taller:

| Tabla | Índice actual | Índice nuevo |
|-------|--------------|--------------|
| `vehiculos` | `UNIQUE(placa)` | `UNIQUE(taller_id, placa)` |
| `tickets` | `UNIQUE(ticket_codigo)` | `UNIQUE(taller_id, ticket_codigo)` |

Esto permite que dos talleres distintos registren la misma placa o el mismo código de ticket.

---

## 5. TenantRepository — Clase Base

### Archivo: `app/repositorios/tenant_repository.py`

```python
from sqlalchemy.orm import Session
from app.utils.exceptions import MissingTenantContextError


class TenantRepository:
    """
    Clase base para repositorios de entidades tenant-aware.
    Aplica automáticamente el filtro taller_id en todas las operaciones.
    """

    model = None  # Subclases deben definir el modelo SQLAlchemy

    def __init__(self, db: Session, taller_id: int):
        if not taller_id:
            raise MissingTenantContextError("taller_id es requerido para operaciones tenant-aware")
        self.db = db
        self.taller_id = taller_id

    def _base_query(self):
        """Query base con filtro de tenant aplicado."""
        return self.db.query(self.model).filter(self.model.taller_id == self.taller_id)

    def get_all(self, skip: int = 0, limit: int = 50):
        return self._base_query().offset(skip).limit(limit).all()

    def get_by_id(self, record_id: int):
        """Retorna None si el registro no pertenece al taller (como si no existiera)."""
        return self._base_query().filter(self.model.id == record_id).first()

    def create(self, record):
        record.taller_id = self.taller_id
        self.db.add(record)
        self.db.flush()
        return record

    def update(self, record):
        self.db.flush()
        return record

    def delete(self, record_id: int) -> bool:
        record = self.get_by_id(record_id)
        if not record:
            return False
        self.db.delete(record)
        self.db.flush()
        return True
```

### Nueva excepción: `app/utils/exceptions.py`

Agregar:

```python
class MissingTenantContextError(Exception):
    """Se lanza cuando se intenta operar sin contexto de taller."""
    pass
```

---

## 6. Refactorización de Repositorios Existentes

Todos los repositorios operativos heredan de `TenantRepository`:

```python
# Ejemplo: ticket_repository.py
class TicketRepository(TenantRepository):
    model = Ticket

    def __init__(self, db: Session, taller_id: int):
        super().__init__(db, taller_id)

    def get_by_codigo(self, ticket_codigo: str) -> Ticket | None:
        return (
            self._base_query()
            .filter(Ticket.ticket_codigo == ticket_codigo.strip().upper())
            .first()
        )

    def get_all(self, skip=0, limit=50, estado=None, placa=None):
        query = self._base_query()
        if estado:
            query = query.filter(Ticket.estado == estado.upper())
        if placa:
            query = query.filter(Ticket.placa.ilike(f"%{placa.strip()}%"))
        return query.order_by(Ticket.fecha_ingreso.desc()).offset(skip).limit(limit).all()
    # ... resto de métodos específicos
```

Repositorios a refactorizar:
- `TicketRepository`
- `VehiculoRepository`
- `CitaRepository`
- `MovimientoCajaRepository`
- `UserRepository` (parcial — `get_all` filtra por taller, pero `get_by_username`/`get_by_email` no)

---

## 7. Cambios en TokenManager

### `app/seguridad/token_manager.py`

Agregar `taller_id` al payload del access token:

```python
def generate_access_token(self, user: User) -> str:
    payload = {
        "user_id": user.id,
        "username": user.username,
        "roles": role_names,
        "taller_id": user.taller_id,   # ← NUEVO
        "exp": expires_at,
        "iat": now,
        "jti": str(uuid.uuid4()),
        "token_type": "access",
    }
```

---

## 8. Cambios en AuthMiddleware

### `app/seguridad/auth_middleware.py`

Dos cambios principales en el método `dispatch`:

**a) Inyectar `taller_id` en `request.state`:**

```python
# Después de validar el usuario
request.state.user = user
request.state.taller_id = payload.get("taller_id")  # ← NUEVO
```

**b) Verificar que el taller esté activo:**

```python
# Verificar taller activo (después de obtener el usuario)
if user.taller_id:
    from app.modelos.taller import Taller
    taller = db.query(Taller).filter(Taller.id == user.taller_id).first()
    if not taller or not taller.activo:
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"detail": "Taller inactivo"},
        )
```

**c) Validar consistencia JWT vs BD:**

```python
jwt_taller_id = payload.get("taller_id")
if jwt_taller_id and jwt_taller_id != user.taller_id:
    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={"detail": "Contexto de taller inválido"},
    )
```

---

## 9. Patrón de Uso en Rutas

Los endpoints extraen `taller_id` de `request.state`, nunca del body o query params:

```python
@router.get("/tickets")
@require_auth
async def listar_tickets(request: Request, db: Session = Depends(obtener_db)):
    taller_id = request.state.taller_id  # ← siempre del JWT
    repo = TicketRepository(db, taller_id)
    return repo.get_all()
```

---

## 10. Nuevo Repositorio y Rutas de Talleres

### `app/repositorios/taller_repository.py`

```python
class TallerRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, taller_id: int) -> Taller | None:
        return self.db.query(Taller).filter(Taller.id == taller_id).first()

    def get_all(self) -> list[Taller]:
        return self.db.query(Taller).order_by(Taller.nombre).all()

    def get_by_nombre(self, nombre: str) -> Taller | None:
        return self.db.query(Taller).filter(Taller.nombre == nombre).first()

    def create(self, taller: Taller) -> Taller:
        self.db.add(taller)
        self.db.flush()
        return taller

    def update(self, taller: Taller) -> Taller:
        self.db.flush()
        return taller
```

### `app/rutas/taller_ruta.py`

Endpoints protegidos con `@require_role("SUPER_ADMIN")`:

- `POST /talleres` — crear taller + configuración por defecto
- `GET /talleres` — listar todos los talleres
- `GET /talleres/{id}` — obtener taller por ID
- `PATCH /talleres/{id}` — actualizar / desactivar taller

---

## 11. Migración Alembic

### Orden de operaciones (una sola transacción):

```sql
-- 1. Crear tabla talleres
CREATE TABLE talleres (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(200) UNIQUE NOT NULL,
    nit VARCHAR(50),
    direccion VARCHAR(300),
    telefono VARCHAR(50),
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    fecha_creacion TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    fecha_actualizacion TIMESTAMPTZ
);

-- 2. Insertar Taller Default
INSERT INTO talleres (nombre, activo) VALUES ('Taller Principal', TRUE);

-- 3. Agregar columnas taller_id (nullable primero)
ALTER TABLE users ADD COLUMN taller_id INTEGER;
ALTER TABLE vehiculos ADD COLUMN taller_id INTEGER;
ALTER TABLE tickets ADD COLUMN taller_id INTEGER;
ALTER TABLE citas ADD COLUMN taller_id INTEGER;
ALTER TABLE movimientos_caja ADD COLUMN taller_id INTEGER;
ALTER TABLE mecanicos ADD COLUMN taller_id INTEGER;
ALTER TABLE ticket_repuestos ADD COLUMN taller_id INTEGER;
ALTER TABLE ticket_procesos ADD COLUMN taller_id INTEGER;
ALTER TABLE ticket_cobros ADD COLUMN taller_id INTEGER;
ALTER TABLE ticket_compras ADD COLUMN taller_id INTEGER;
ALTER TABLE ticket_fotos ADD COLUMN taller_id INTEGER;
ALTER TABLE cambios_movimiento_caja ADD COLUMN taller_id INTEGER;
ALTER TABLE log_notificacion ADD COLUMN taller_id INTEGER;
ALTER TABLE audit_log ADD COLUMN taller_id INTEGER;
ALTER TABLE configuracion_taller ADD COLUMN taller_id INTEGER;

-- 4. Asignar Taller Default a todos los registros existentes
UPDATE users SET taller_id = (SELECT id FROM talleres WHERE nombre = 'Taller Principal');
UPDATE vehiculos SET taller_id = (SELECT id FROM talleres WHERE nombre = 'Taller Principal');
UPDATE tickets SET taller_id = (SELECT id FROM talleres WHERE nombre = 'Taller Principal');
UPDATE citas SET taller_id = (SELECT id FROM talleres WHERE nombre = 'Taller Principal');
UPDATE movimientos_caja SET taller_id = (SELECT id FROM talleres WHERE nombre = 'Taller Principal');
UPDATE mecanicos SET taller_id = (SELECT id FROM talleres WHERE nombre = 'Taller Principal');
UPDATE ticket_repuestos SET taller_id = (SELECT id FROM talleres WHERE nombre = 'Taller Principal');
UPDATE ticket_procesos SET taller_id = (SELECT id FROM talleres WHERE nombre = 'Taller Principal');
UPDATE ticket_cobros SET taller_id = (SELECT id FROM talleres WHERE nombre = 'Taller Principal');
UPDATE ticket_compras SET taller_id = (SELECT id FROM talleres WHERE nombre = 'Taller Principal');
UPDATE ticket_fotos SET taller_id = (SELECT id FROM talleres WHERE nombre = 'Taller Principal');
UPDATE cambios_movimiento_caja SET taller_id = (SELECT id FROM talleres WHERE nombre = 'Taller Principal');
UPDATE log_notificacion SET taller_id = (SELECT id FROM talleres WHERE nombre = 'Taller Principal');
-- audit_log y configuracion_taller: nullable, no requieren UPDATE obligatorio

-- 5. Agregar NOT NULL y FK (excepto audit_log que es nullable)
ALTER TABLE users ALTER COLUMN taller_id SET NOT NULL;
ALTER TABLE users ADD CONSTRAINT fk_users_taller FOREIGN KEY (taller_id) REFERENCES talleres(id);
-- (repetir para cada tabla operativa)

-- 6. Eliminar índice único global y crear compuesto
DROP INDEX ix_vehiculos_placa;
CREATE UNIQUE INDEX ix_vehiculos_taller_placa ON vehiculos(taller_id, placa);

DROP INDEX ix_tickets_ticket_codigo;
CREATE UNIQUE INDEX ix_tickets_taller_codigo ON tickets(taller_id, ticket_codigo);

-- 7. Crear índices compuestos de rendimiento
CREATE INDEX ix_tickets_taller_estado ON tickets(taller_id, estado);
CREATE INDEX ix_citas_taller_fecha ON citas(taller_id, fecha_cita);
CREATE INDEX ix_movimientos_taller_fecha ON movimientos_caja(taller_id, fecha_creacion);
```

---

## 12. Propiedades de Corrección (Property-Based Testing)

Las siguientes propiedades deben ser verificables mediante tests automatizados:

### P1 — Aislamiento de lectura
Para cualquier usuario U con `taller_id = T`, toda query de listado retorna únicamente registros donde `registro.taller_id == T`.

### P2 — Aislamiento de escritura
Para cualquier operación de creación ejecutada por usuario U con `taller_id = T`, el registro creado tiene `taller_id == T` independientemente de cualquier valor enviado en el body.

### P3 — Opacidad cross-tenant
Para cualquier `id` de recurso que pertenece al taller T2, una petición de usuario con `taller_id = T1` (T1 ≠ T2) retorna HTTP 404, nunca HTTP 403 ni el recurso.

### P4 — Integridad referencial
Para cualquier Ticket creado con `vehiculo_id = V`, el Vehiculo con id=V tiene `taller_id == ticket.taller_id`.

### P5 — Contexto inmutable
El `taller_id` efectivo en cualquier operación es siempre el del JWT del usuario autenticado, nunca un valor proveniente del body, query params o headers del cliente.

### P6 — Taller inactivo bloquea acceso
Si `taller.activo == False`, ningún usuario de ese taller puede autenticarse ni acceder a endpoints protegidos.

---

## 13. Resumen de Archivos Afectados

| Acción | Archivos |
|--------|---------|
| **Crear nuevos** | `app/modelos/taller.py`, `app/repositorios/taller_repository.py`, `app/repositorios/tenant_repository.py`, `app/rutas/taller_ruta.py`, `app/servicios/taller_service.py`, `app/esquemas/taller_schema.py` |
| **Modificar modelos** | `app/modelos/user.py`, `app/modelos/ticket.py`, `app/modelos/vehiculo.py`, `app/modelos/cita.py`, `app/modelos/movimiento_caja.py`, `app/modelos/mecanico.py`, `app/modelos/ticket_repuesto.py`, `app/modelos/ticket_proceso.py`, `app/modelos/ticket_cobro.py`, `app/modelos/ticket_compra.py`, `app/modelos/ticket_foto.py`, `app/modelos/cambio_movimiento_caja.py`, `app/modelos/log_notificacion.py`, `app/modelos/audit_log.py`, `app/modelos/configuracion_taller.py` |
| **Modificar seguridad** | `app/seguridad/auth_middleware.py`, `app/seguridad/token_manager.py` |
| **Refactorizar repositorios** | `app/repositorios/ticket_repository.py`, `app/repositorios/vehiculo_repository.py`, `app/repositorios/cita_repository.py`, `app/repositorios/movimiento_caja_repository.py`, `app/repositorios/user_repository.py` |
| **Modificar utils** | `app/utils/exceptions.py` |
| **Modificar main** | `app/main.py` (registrar router de talleres) |
| **Crear migración** | `alembic/versions/xxxx_add_multi_tenant_taller_id.py` |
