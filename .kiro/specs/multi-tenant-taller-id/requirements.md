# Documento de Requisitos

## Introducción

Este documento describe los requisitos para implementar un sistema **multi-tenant** en la aplicación de gestión de taller mecánico (FastAPI + PostgreSQL). El objetivo es aislar completamente los datos de cada taller mediante un discriminador `taller_id` en todos los registros del sistema, de modo que múltiples talleres puedan operar sobre la misma instancia de la aplicación sin que sus datos se mezclen.

El sistema actual tiene una sola instancia de datos (single-tenant). La migración debe ser no destructiva: los datos existentes se asignarán a un taller por defecto, y el sistema de seguridad existente (JWT, RBAC, audit log, rate limiting) se extenderá para incorporar el contexto de taller en cada operación.

---

## Glosario

- **Taller**: Entidad raíz del sistema multi-tenant. Representa un negocio de taller mecánico independiente. Identificado por `taller_id`.
- **Sistema**: La aplicación FastAPI + PostgreSQL de gestión de taller mecánico.
- **Tenant**: Sinónimo de Taller en este contexto. Cada taller es un tenant aislado.
- **taller_id**: Clave foránea entera que referencia a la tabla `talleres` y actúa como discriminador de tenant en todas las tablas de datos.
- **Contexto_de_Taller**: El `taller_id` asociado al usuario autenticado, extraído del JWT o del perfil del usuario en la base de datos.
- **Usuario**: Persona autenticada en el sistema, siempre asociada a exactamente un Taller.
- **ADMIN**: Rol de administrador del sistema con acceso completo dentro de su Taller.
- **MECANICO**: Rol de mecánico con acceso operativo dentro de su Taller.
- **Super_Admin**: Rol especial con acceso de lectura a todos los talleres, reservado para administración de la plataforma.
- **Registro_Tenant**: Cualquier fila en una tabla que contiene `taller_id` como columna discriminadora.
- **Aislamiento**: Garantía de que un usuario de un Taller no puede leer, crear, modificar ni eliminar datos de otro Taller.
- **Migración**: Proceso de añadir `taller_id` a las tablas existentes y asignar los datos actuales al Taller por defecto.
- **Taller_Default**: El primer taller creado durante la migración, al que se asignan todos los datos preexistentes.
- **Repositorio**: Capa de acceso a datos (archivos `*_repository.py`) que ejecuta queries contra la base de datos.
- **Servicio**: Capa de lógica de negocio (archivos `*_service.py`) que orquesta operaciones.
- **Middleware_Tenant**: Componente que extrae y valida el `taller_id` del usuario autenticado e inyecta el Contexto_de_Taller en cada request.
- **Audit_Log**: Registro inmutable de acciones del sistema, extendido para incluir `taller_id`.

---

## Requisitos

### Requisito 1: Modelo de Taller (Entidad Raíz del Tenant)

**User Story:** Como administrador de la plataforma, quiero que cada taller sea una entidad independiente en la base de datos, para que el sistema pueda gestionar múltiples talleres de forma aislada.

#### Criterios de Aceptación

1. THE Sistema SHALL crear una tabla `talleres` con los campos: `id` (PK), `nombre` (string, obligatorio), `nit` (string, opcional), `direccion` (string, opcional), `telefono` (string, opcional), `activo` (boolean, default true), `fecha_creacion` (timestamp), `fecha_actualizacion` (timestamp).
2. THE Sistema SHALL garantizar que el campo `nombre` de la tabla `talleres` sea único y no nulo.
3. WHEN se crea un Taller, THE Sistema SHALL asignar automáticamente `activo = true` y registrar `fecha_creacion` con la marca de tiempo actual.
4. IF se intenta crear un Taller con `nombre` duplicado, THEN THE Sistema SHALL retornar un error HTTP 409 con el mensaje "Ya existe un taller con ese nombre".
5. THE Sistema SHALL migrar la configuración existente de `configuracion_taller` al primer Taller creado (Taller_Default) durante la migración inicial.

---

### Requisito 2: Asociación de Usuarios a un Taller

**User Story:** Como administrador, quiero que cada usuario pertenezca a exactamente un taller, para que el sistema pueda determinar automáticamente qué datos puede ver y modificar cada usuario.

#### Criterios de Aceptación

1. THE Sistema SHALL añadir la columna `taller_id` (FK → `talleres.id`, NOT NULL) a la tabla `users`.
2. WHEN un usuario se autentica exitosamente, THE Sistema SHALL incluir el `taller_id` del usuario en el payload del JWT como campo `taller_id`.
3. THE Middleware_Tenant SHALL extraer el `taller_id` del JWT del usuario autenticado e inyectarlo en `request.state.taller_id` en cada request.
4. IF un usuario no tiene `taller_id` asignado, THEN THE Sistema SHALL rechazar la autenticación con HTTP 403 y el mensaje "Usuario sin taller asignado".
5. THE Sistema SHALL asignar todos los usuarios existentes al Taller_Default durante la migración inicial.
6. WHEN se crea un usuario nuevo, THE Sistema SHALL requerir que se especifique un `taller_id` válido y existente.
7. IF se intenta asignar un usuario a un Taller con `activo = false`, THEN THE Sistema SHALL retornar HTTP 400 con el mensaje "El taller especificado no está activo".

---

### Requisito 3: Aislamiento de Datos en Todas las Tablas Operativas

**User Story:** Como propietario de un taller, quiero que los datos de mi taller estén completamente aislados de los de otros talleres, para que no haya fuga de información entre negocios.

#### Criterios de Aceptación

1. THE Sistema SHALL añadir la columna `taller_id` (FK → `talleres.id`, NOT NULL, indexed) a las siguientes tablas: `vehiculos`, `tickets`, `citas`, `movimientos_caja`, `mecanicos`, `ticket_repuestos`, `ticket_procesos`, `ticket_cobros`, `ticket_compras`, `ticket_fotos`, `cambios_movimiento_caja`, `log_notificacion`.
2. WHEN un Repositorio ejecuta una query de lectura (SELECT), THE Repositorio SHALL incluir siempre el filtro `WHERE taller_id = :taller_id` usando el Contexto_de_Taller del request.
3. WHEN un Repositorio ejecuta una operación de escritura (INSERT), THE Repositorio SHALL asignar automáticamente el `taller_id` del Contexto_de_Taller al nuevo registro.
4. WHEN un Repositorio ejecuta una operación de actualización o eliminación (UPDATE/DELETE), THE Repositorio SHALL incluir siempre el filtro `WHERE taller_id = :taller_id` para prevenir modificaciones cruzadas entre talleres.
5. IF una query de lectura o escritura se ejecuta sin Contexto_de_Taller disponible, THEN THE Sistema SHALL lanzar una excepción interna `MissingTenantContextError` y retornar HTTP 500 al cliente.
6. THE Sistema SHALL asignar el Taller_Default como `taller_id` a todos los registros existentes en las tablas listadas en el criterio 1 durante la migración inicial.
7. WHILE el sistema está en operación, THE Sistema SHALL garantizar que ninguna query de lectura retorne registros de un `taller_id` distinto al del usuario autenticado, salvo para el rol Super_Admin.

---

### Requisito 4: Filtrado Automático por Tenant en la Capa de Repositorio

**User Story:** Como desarrollador, quiero que el filtrado por `taller_id` sea automático y centralizado en la capa de repositorio, para que no sea posible olvidar aplicarlo en ningún endpoint.

#### Criterios de Aceptación

1. THE Sistema SHALL implementar una clase base `TenantRepository` que todos los repositorios de entidades tenant-aware deberán extender.
2. THE TenantRepository SHALL exponer métodos `get_all`, `get_by_id`, `create`, `update` y `delete` que apliquen automáticamente el filtro `taller_id` en todas las operaciones.
3. WHEN se llama a `get_by_id` con un `id` que existe pero pertenece a un `taller_id` diferente al del Contexto_de_Taller, THE TenantRepository SHALL retornar `None` (como si el registro no existiera).
4. IF un repositorio hereda de `TenantRepository` y no recibe `taller_id` en su constructor, THEN THE TenantRepository SHALL lanzar `MissingTenantContextError` antes de ejecutar cualquier query.
5. THE Sistema SHALL garantizar que los repositorios existentes (`ticket_repository`, `vehiculo_repository`, `cita_repository`, `movimiento_caja_repository`, `user_repository`) sean refactorizados para extender `TenantRepository`.

---

### Requisito 5: Integridad Referencial entre Entidades del Mismo Taller

**User Story:** Como administrador, quiero que las relaciones entre entidades (por ejemplo, un ticket referenciando un vehículo) solo sean posibles dentro del mismo taller, para evitar inconsistencias de datos entre tenants.

#### Criterios de Aceptación

1. WHEN se crea un Ticket con un `vehiculo_id`, THE Sistema SHALL verificar que el Vehiculo referenciado pertenece al mismo `taller_id` que el Ticket antes de persistir.
2. WHEN se crea una Cita con un `vehiculo_id`, THE Sistema SHALL verificar que el Vehiculo referenciado pertenece al mismo `taller_id` que la Cita antes de persistir.
3. WHEN se crea un MovimientoCaja con un `ticket_id`, THE Sistema SHALL verificar que el Ticket referenciado pertenece al mismo `taller_id` que el MovimientoCaja antes de persistir.
4. IF una verificación de integridad cross-tenant falla, THEN THE Sistema SHALL retornar HTTP 400 con el mensaje "El recurso referenciado no pertenece a este taller".
5. THE Sistema SHALL aplicar estas verificaciones en la capa de Servicio, antes de delegar al Repositorio.

---

### Requisito 6: Seguridad y Control de Acceso por Tenant

**User Story:** Como propietario de un taller, quiero que el sistema rechace activamente cualquier intento de acceder a datos de otro taller, incluso si el usuario manipula parámetros de la petición.

#### Criterios de Aceptación

1. THE Sistema SHALL derivar el Contexto_de_Taller exclusivamente del JWT del usuario autenticado, nunca de parámetros de query, body o headers enviados por el cliente.
2. WHEN un endpoint recibe un `taller_id` en el body o query params que difiere del Contexto_de_Taller del usuario autenticado, THE Sistema SHALL ignorar el valor del cliente y usar el Contexto_de_Taller del JWT.
3. THE Sistema SHALL registrar en el Audit_Log toda operación de lectura o escritura sobre datos de un Taller, incluyendo el `taller_id` del Contexto_de_Taller como campo del log.
4. IF se detecta un intento de acceso a un recurso de un `taller_id` diferente al del usuario autenticado (por ejemplo, mediante manipulación de IDs en la URL), THEN THE Sistema SHALL retornar HTTP 404 (no 403) para no revelar la existencia del recurso.
5. WHERE el rol Super_Admin está activo, THE Sistema SHALL permitir consultas de lectura entre talleres únicamente a través de endpoints específicos protegidos con `@require_role("SUPER_ADMIN")`.
6. THE Sistema SHALL extender el modelo `AuditLog` con la columna `taller_id` (FK → `talleres.id`, nullable) para registrar el contexto de taller en cada acción auditada.

---

### Requisito 7: Configuración Independiente por Taller

**User Story:** Como propietario de un taller, quiero que la configuración de mi taller (nombre, logo, procesos rápidos, cobros rápidos, WhatsApp) sea independiente de la de otros talleres, para personalizar mi operación sin afectar a otros.

#### Criterios de Aceptación

1. THE Sistema SHALL asociar la tabla `configuracion_taller` a un único Taller mediante una relación 1:1 con `taller_id` (FK → `talleres.id`, UNIQUE, NOT NULL).
2. WHEN un usuario autenticado consulta la configuración del taller, THE Sistema SHALL retornar únicamente la configuración del Taller correspondiente a su Contexto_de_Taller.
3. WHEN un usuario con rol ADMIN modifica la configuración del taller, THE Sistema SHALL aplicar los cambios únicamente a la configuración del Taller de su Contexto_de_Taller.
4. IF no existe una fila de `configuracion_taller` para el Taller del usuario autenticado, THEN THE Sistema SHALL crear automáticamente una configuración con valores por defecto al primer acceso.
5. THE Sistema SHALL migrar la fila existente de `configuracion_taller` para asociarla al Taller_Default durante la migración inicial.

---

### Requisito 8: Migración de Datos Existentes

**User Story:** Como administrador de la plataforma, quiero que todos los datos existentes sean migrados de forma segura al nuevo esquema multi-tenant, para que el sistema no pierda información durante la transición.

#### Criterios de Aceptación

1. THE Sistema SHALL crear un script de migración SQL (Alembic) que añada la columna `taller_id` a todas las tablas listadas en el Requisito 3, criterio 1, más la tabla `users`.
2. THE Script_Migracion SHALL crear primero el Taller_Default con `nombre = "Taller Principal"` antes de añadir las columnas `taller_id`.
3. THE Script_Migracion SHALL asignar el `id` del Taller_Default como valor de `taller_id` en todos los registros existentes de todas las tablas afectadas, en una sola transacción.
4. THE Script_Migracion SHALL añadir las restricciones `NOT NULL` y `FOREIGN KEY` sobre `taller_id` únicamente después de que todos los registros existentes tengan el valor asignado.
5. THE Script_Migracion SHALL crear índices sobre `taller_id` en todas las tablas afectadas para garantizar rendimiento en las queries filtradas.
6. IF el Script_Migracion falla en cualquier paso, THEN THE Script_Migracion SHALL hacer rollback completo de la transacción sin dejar el esquema en estado inconsistente.
7. THE Sistema SHALL proveer un script de rollback que revierta todos los cambios del Script_Migracion de forma segura.

---

### Requisito 9: Rendimiento de Queries Multi-Tenant

**User Story:** Como usuario del sistema, quiero que las consultas filtradas por taller sean igual de rápidas que las consultas actuales, para que el multi-tenant no degrade la experiencia de uso.

#### Criterios de Aceptación

1. THE Sistema SHALL crear índices compuestos `(taller_id, <campo_principal>)` en las tablas de alta frecuencia de consulta: `tickets(taller_id, estado)`, `vehiculos(taller_id, placa)`, `citas(taller_id, fecha_cita)`, `movimientos_caja(taller_id, fecha_creacion)`.
2. WHEN se ejecuta una query de listado sobre cualquier tabla tenant-aware, THE Repositorio SHALL incluir `taller_id` como primer filtro en la cláusula WHERE para aprovechar los índices compuestos.
3. THE Sistema SHALL mantener el índice único existente sobre `vehiculos.placa` como índice único compuesto `(taller_id, placa)`, permitiendo que dos talleres distintos registren el mismo número de placa.
4. THE Sistema SHALL mantener el índice único existente sobre `tickets.ticket_codigo` como índice único compuesto `(taller_id, ticket_codigo)`, permitiendo que dos talleres distintos usen el mismo código de ticket.

---

### Requisito 10: API de Gestión de Talleres (Solo Super_Admin)

**User Story:** Como administrador de la plataforma, quiero una API para crear y gestionar talleres, para poder incorporar nuevos clientes al sistema sin acceso directo a la base de datos.

#### Criterios de Aceptación

1. THE Sistema SHALL exponer los endpoints `POST /talleres`, `GET /talleres`, `GET /talleres/{id}`, `PATCH /talleres/{id}` protegidos con `@require_role("SUPER_ADMIN")`.
2. WHEN se crea un Taller mediante `POST /talleres`, THE Sistema SHALL crear automáticamente una fila de `configuracion_taller` con valores por defecto asociada al nuevo Taller.
3. WHEN se desactiva un Taller mediante `PATCH /talleres/{id}` con `activo = false`, THE Sistema SHALL impedir el login de todos los usuarios asociados a ese Taller retornando HTTP 403 con el mensaje "Taller inactivo".
4. IF se intenta desactivar el Taller_Default, THEN THE Sistema SHALL retornar HTTP 400 con el mensaje "No se puede desactivar el taller principal".
5. THE Sistema SHALL registrar en el Audit_Log toda operación de creación, modificación o desactivación de un Taller, con la acción `TALLER_CREATE`, `TALLER_UPDATE` o `TALLER_DEACTIVATE` respectivamente.

---

### Requisito 11: Compatibilidad con el Sistema de Seguridad Existente

**User Story:** Como administrador de seguridad, quiero que el multi-tenant se integre con el sistema de seguridad existente (JWT, RBAC, audit log, rate limiting) sin degradar las garantías actuales.

#### Criterios de Aceptación

1. THE Sistema SHALL mantener todos los mecanismos de seguridad existentes: JWT con blacklist, `@require_auth`, `@require_role`, rate limiting, detección de fuerza bruta y audit log.
2. WHEN el AuthMiddleware valida un token JWT, THE AuthMiddleware SHALL verificar adicionalmente que el Taller asociado al usuario tiene `activo = true`; si no, retornará HTTP 403.
3. THE Sistema SHALL extender el payload del JWT para incluir `taller_id`, sin modificar los campos existentes (`user_id`, `jti`, `exp`, `roles`).
4. WHEN se genera un nuevo access token o refresh token, THE Token_Manager SHALL incluir el `taller_id` del usuario en el payload.
5. IF el `taller_id` en el JWT no coincide con el `taller_id` almacenado en la base de datos para ese usuario, THEN THE AuthMiddleware SHALL invalidar la sesión y retornar HTTP 401 con el mensaje "Contexto de taller inválido".
6. THE Sistema SHALL aplicar rate limiting de forma independiente por `(IP, taller_id)` para evitar que el abuso desde un taller afecte a otros.
