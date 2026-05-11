# Tareas de Implementación: Multi-Tenant con taller_id

## Resumen

Implementación del sistema multi-tenant completo. Las tareas están ordenadas para que cada una sea ejecutable sin romper el sistema: primero la base de datos y modelos, luego la capa de repositorios, luego seguridad, y finalmente las rutas y migración.

---

## Tareas

- [x] 1. Crear modelo Taller y excepción MissingTenantContextError
  - [x] 1.1 Crear `app/modelos/taller.py` con el modelo `Taller` (campos: id, nombre, nit, direccion, telefono, activo, fecha_creacion, fecha_actualizacion)
  - [x] 1.2 Agregar `MissingTenantContextError` a `app/utils/exceptions.py`
  - [x] 1.3 Registrar el modelo `Taller` en `app/modelos/__init__.py`

- [x] 2. Agregar taller_id a todos los modelos SQLAlchemy
  - [x] 2.1 Agregar `taller_id = Column(Integer, ForeignKey("talleres.id"), nullable=False, index=True)` y relación `taller` a `app/modelos/user.py`
  - [x] 2.2 Agregar `taller_id` a `app/modelos/ticket.py` y cambiar `ticket_codigo` de `unique=True` a sin unique (el índice único compuesto se crea en migración)
  - [x] 2.3 Agregar `taller_id` a `app/modelos/vehiculo.py` y cambiar `placa` de `unique=True` a sin unique
  - [x] 2.4 Agregar `taller_id` a `app/modelos/cita.py`
  - [x] 2.5 Agregar `taller_id` a `app/modelos/movimiento_caja.py`
  - [x] 2.6 Agregar `taller_id` a `app/modelos/mecanico.py`
  - [x] 2.7 Agregar `taller_id` a `app/modelos/ticket_repuesto.py`
  - [x] 2.8 Agregar `taller_id` a `app/modelos/ticket_proceso.py`
  - [x] 2.9 Agregar `taller_id` a `app/modelos/ticket_cobro.py`
  - [x] 2.10 Agregar `taller_id` a `app/modelos/ticket_compra.py`
  - [x] 2.11 Agregar `taller_id` a `app/modelos/ticket_foto.py`
  - [x] 2.12 Agregar `taller_id` a `app/modelos/cambio_movimiento_caja.py`
  - [x] 2.13 Agregar `taller_id` a `app/modelos/log_notificacion.py`
  - [x] 2.14 Agregar `taller_id` (nullable) a `app/modelos/audit_log.py` y nuevas acciones `TALLER_CREATE`, `TALLER_UPDATE`, `TALLER_DEACTIVATE` al enum `AuditAction`
  - [x] 2.15 Agregar `taller_id` (unique, FK) y relación a `app/modelos/configuracion_taller.py`

- [x] 3. Crear TenantRepository y refactorizar repositorios existentes
  - [x] 3.1 Crear `app/repositorios/tenant_repository.py` con la clase base `TenantRepository` que aplica filtro `taller_id` automáticamente en `get_all`, `get_by_id`, `create`, `update`, `delete`
  - [x] 3.2 Refactorizar `app/repositorios/ticket_repository.py` para heredar de `TenantRepository` — constructor recibe `(db, taller_id)`, todos los métodos usan `self._base_query()`
  - [x] 3.3 Refactorizar `app/repositorios/vehiculo_repository.py` para heredar de `TenantRepository` — `get_by_placa` filtra por taller, `search` filtra por taller
  - [x] 3.4 Refactorizar `app/repositorios/cita_repository.py` para heredar de `TenantRepository`
  - [x] 3.5 Refactorizar `app/repositorios/movimiento_caja_repository.py` para heredar de `TenantRepository`
  - [x] 3.6 Actualizar `app/repositorios/user_repository.py` — `get_all` filtra por `taller_id`, pero `get_by_username` y `get_by_email` permanecen globales (necesarios para autenticación)

- [x] 4. Crear repositorio y servicio de Taller
  - [x] 4.1 Crear `app/repositorios/taller_repository.py` con métodos: `get_by_id`, `get_all`, `get_by_nombre`, `create`, `update`
  - [x] 4.2 Crear `app/servicios/taller_service.py` con métodos: `crear_taller` (crea taller + configuración por defecto), `obtener_taller`, `listar_talleres`, `actualizar_taller`, `desactivar_taller` (verifica que no sea el Taller_Default)
  - [x] 4.3 Crear `app/esquemas/taller_schema.py` con schemas Pydantic: `TallerCreate`, `TallerUpdate`, `TallerResponse`

- [x] 5. Actualizar TokenManager para incluir taller_id en JWT
  - [x] 5.1 Modificar `generate_access_token` en `app/seguridad/token_manager.py` para incluir `"taller_id": user.taller_id` en el payload
  - [x] 5.2 Verificar que `generate_refresh_token` no necesita `taller_id` (el refresh token solo necesita `user_id`)

- [x] 6. Actualizar AuthMiddleware para contexto multi-tenant
  - [x] 6.1 Modificar `app/seguridad/auth_middleware.py` — extraer `taller_id` del payload JWT e inyectar en `request.state.taller_id`
  - [x] 6.2 Agregar verificación de taller activo: después de obtener el usuario, consultar `Taller` y retornar HTTP 403 si `taller.activo == False`
  - [x] 6.3 Agregar validación de consistencia: si `payload["taller_id"] != user.taller_id`, retornar HTTP 401 con mensaje "Contexto de taller inválido"

- [x] 7. Actualizar servicios existentes para pasar taller_id
  - [x] 7.1 Actualizar `app/servicios/ticket_service.py` — recibir `taller_id` como parámetro, pasarlo al `TicketRepository`, verificar que `vehiculo_id` pertenece al mismo taller antes de crear ticket
  - [x] 7.2 Actualizar `app/servicios/vehiculo_service.py` — recibir `taller_id`, pasarlo al `VehiculoRepository`
  - [x] 7.3 Actualizar `app/servicios/cita_service.py` — recibir `taller_id`, pasarlo al `CitaRepository`, verificar que `vehiculo_id` pertenece al mismo taller
  - [x] 7.4 Actualizar `app/servicios/movimiento_caja_service.py` — recibir `taller_id`, pasarlo al `MovimientoCajaRepository`, verificar que `ticket_id` pertenece al mismo taller
  - [x] 7.5 Actualizar `app/servicios/user_service.py` — recibir `taller_id` al crear usuario, verificar que el taller existe y está activo

- [x] 8. Actualizar rutas para extraer taller_id de request.state
  - [x] 8.1 Actualizar `app/rutas/ticket_ruta.py` — extraer `taller_id = request.state.taller_id` y pasarlo al servicio en todos los endpoints
  - [x] 8.2 Actualizar `app/rutas/vehiculo_ruta.py` — extraer `taller_id` de `request.state`
  - [x] 8.3 Actualizar `app/rutas/citas_ruta.py` — extraer `taller_id` de `request.state`
  - [x] 8.4 Actualizar `app/rutas/movimiento_caja_ruta.py` — extraer `taller_id` de `request.state`
  - [x] 8.5 Actualizar `app/rutas/users_ruta.py` — extraer `taller_id` de `request.state` para operaciones de listado y creación
  - [x] 8.6 Actualizar `app/rutas/configuracion_ruta.py` — filtrar configuración por `taller_id` del usuario autenticado
  - [x] 8.7 Crear `app/rutas/taller_ruta.py` con endpoints `POST /talleres`, `GET /talleres`, `GET /talleres/{id}`, `PATCH /talleres/{id}` protegidos con `@require_role("SUPER_ADMIN")`
  - [x] 8.8 Registrar `taller_ruta` en `app/main.py`

- [x] 9. Crear migración Alembic
  - [x] 9.1 Crear archivo de migración Alembic en `alembic/versions/` con función `upgrade()` que: crea tabla `talleres`, inserta Taller_Default, agrega columnas `taller_id` nullable a todas las tablas, ejecuta UPDATEs para asignar Taller_Default, agrega NOT NULL y FK constraints, elimina índices únicos globales y crea índices únicos compuestos `(taller_id, placa)` y `(taller_id, ticket_codigo)`, crea índices compuestos de rendimiento
  - [x] 9.2 Implementar función `downgrade()` en la misma migración que revierte todos los cambios en orden inverso

- [x] 10. Escribir tests de propiedades (Property-Based Testing)
  - [x] 10.1 Crear `tests/test_tenant_isolation.py` con test de propiedad P1: para cualquier usuario con `taller_id=T`, `get_all()` retorna solo registros con `taller_id==T`
  - [x] 10.2 Agregar test de propiedad P2: `create()` siempre asigna `taller_id` del contexto, ignorando cualquier valor en el objeto
  - [x] 10.3 Agregar test de propiedad P3: `get_by_id()` con ID de otro taller retorna `None`
  - [x] 10.4 Agregar test de propiedad P4: crear Ticket con `vehiculo_id` de otro taller lanza error HTTP 400
  - [x] 10.5 Agregar test de propiedad P5: `taller_id` en request siempre viene del JWT, nunca del body
  - [x] 10.6 Agregar test de propiedad P6: usuario de taller inactivo recibe HTTP 403 en cualquier endpoint protegido
