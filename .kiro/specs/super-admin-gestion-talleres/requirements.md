# Documento de Requisitos: Super Admin — Gestión de Talleres

## Introducción

Este documento describe los requisitos para el panel de administración de plataforma del **SUPER_ADMIN** en el sistema SaaS de gestión de talleres mecánicos.

El SUPER_ADMIN es el administrador de la plataforma (el desarrollador/empresa que vende el SaaS). No pertenece a ningún taller (`taller_id = NULL`) y tiene control total sobre todos los tenants. Este spec cubre: identidad del SUPER_ADMIN, ciclo de vida de talleres, onboarding de clientes, gestión de usuarios por taller, dashboard de métricas, control de recursos, seguridad de emergencia y auditoría cruzada.

Los temas de planes/facturación, notificaciones internas e internacionalización están en sus propios specs separados.

---

## Glosario

- **SUPER_ADMIN**: Administrador de la plataforma SaaS. `taller_id = NULL`. Se crea solo por script SQL, nunca por endpoint HTTP.
- **Admin_Taller**: Usuario con rol `ADMIN` dentro de un taller específico.
- **Estado_Taller**: `TRIAL`, `ACTIVO`, `SUSPENDIDO`, `CANCELADO`.
- **Bloqueo_Emergencia**: Bloqueo inmediato por seguridad, diferente a `SUSPENDIDO`. No altera el Estado_Taller.
- **Script_Super_Admin**: Archivo `scripts/crear_super_admin.sql` — único método para crear el SUPER_ADMIN.
- **Metricas_Taller**: Conteos operativos de un taller sin datos privados.
- **Metricas_Globales**: Conteos agregados de toda la plataforma.

---

## Requisitos

### Requisito 1: Identidad y Autenticación del SUPER_ADMIN

**User Story:** Como desarrollador de la plataforma, quiero que el SUPER_ADMIN sea una entidad sin afiliación a ningún taller, para que su acceso no dependa del ciclo de vida de ningún tenant.

#### Criterios de Aceptación

1. THE Sistema SHALL permitir que la tabla `users` almacene un usuario con `taller_id = NULL` exclusivamente para el rol `SUPER_ADMIN`.
2. THE Script_Super_Admin SHALL crear el usuario SUPER_ADMIN directamente en la base de datos mediante SQL, sin exponer ningún endpoint HTTP para este propósito.
3. THE Script_Super_Admin SHALL hashear la contraseña del SUPER_ADMIN con bcrypt antes de insertarla en `password_hash`.
4. THE Script_Super_Admin SHALL ser idempotente: si el SUPER_ADMIN ya existe, actualiza la contraseña sin crear duplicados.
5. THE Script_Super_Admin SHALL incluir comentarios que documenten que es el único método autorizado para crear un SUPER_ADMIN y que la contraseña por defecto debe cambiarse antes de producción.
6. WHEN el SUPER_ADMIN se autentica, THE Sistema SHALL emitir un JWT con `taller_id = null` en el payload.
7. WHEN el AuthMiddleware procesa un JWT con `taller_id = null` y rol `SUPER_ADMIN`, THE AuthMiddleware SHALL omitir la verificación de taller activo.
8. IF se intenta crear un usuario con rol `SUPER_ADMIN` mediante cualquier endpoint HTTP, THEN THE Sistema SHALL retornar HTTP 403 con el mensaje "Operación no permitida por API".

---

### Requisito 2: Ciclo de Vida del Taller

**User Story:** Como SUPER_ADMIN, quiero gestionar el estado de cada taller a lo largo de su ciclo de vida, para controlar el acceso según el estado de la suscripción.

#### Criterios de Aceptación

1. THE Sistema SHALL extender la tabla `talleres` con: `estado` (enum: `TRIAL`, `ACTIVO`, `SUSPENDIDO`, `CANCELADO`, default `TRIAL`), `fecha_inicio_trial` (timestamp, nullable), `dias_trial` (integer, nullable), `fecha_suspension` (timestamp, nullable), `fecha_cancelacion` (timestamp, nullable).
2. WHEN se crea un Taller, THE Sistema SHALL asignar `estado = TRIAL`, registrar `fecha_inicio_trial = NOW()` y asignar `dias_trial` al valor especificado por el SUPER_ADMIN.
3. WHEN el SUPER_ADMIN cambia el estado a `ACTIVO`, THE Sistema SHALL registrar la transición en Audit_Log con acción `TALLER_ACTIVATE`.
4. WHEN el SUPER_ADMIN cambia el estado a `SUSPENDIDO`, THE Sistema SHALL registrar `fecha_suspension = NOW()` y acción `TALLER_SUSPEND` en Audit_Log.
5. WHEN el SUPER_ADMIN cambia el estado a `CANCELADO`, THE Sistema SHALL registrar `fecha_cancelacion = NOW()` y acción `TALLER_CANCEL` en Audit_Log.
6. WHILE un Taller tiene `estado = SUSPENDIDO` o `CANCELADO`, THE AuthMiddleware SHALL rechazar requests de sus usuarios con HTTP 403 y mensaje "Taller suspendido. Contacte al administrador de la plataforma.".
7. WHILE un Taller tiene `estado = TRIAL` o `ACTIVO`, THE Sistema SHALL permitir acceso completo a todos sus usuarios.
8. THE Sistema SHALL calcular y retornar `dias_restantes_trial` en `GET /talleres/{id}` como `(fecha_inicio_trial + dias_trial) - NOW()`, retornando `null` si el taller no está en `TRIAL`.
9. IF se intenta cambiar el estado a uno igual al actual, THEN THE Sistema SHALL retornar HTTP 400 con el mensaje "El taller ya se encuentra en el estado especificado".

---

### Requisito 3: CRUD de Talleres

**User Story:** Como SUPER_ADMIN, quiero crear, consultar y actualizar talleres desde la API, para incorporar nuevos clientes sin acceso directo a la base de datos.

#### Criterios de Aceptación

1. THE Sistema SHALL proteger `POST /talleres`, `GET /talleres`, `GET /talleres/{id}`, `PATCH /talleres/{id}` con `@require_role("SUPER_ADMIN")`.
2. WHEN el SUPER_ADMIN crea un Taller, THE Sistema SHALL crear automáticamente una fila en `configuracion_taller` con valores por defecto y retornar HTTP 201.
3. WHEN el SUPER_ADMIN consulta `GET /talleres`, THE Sistema SHALL retornar todos los talleres con: `id`, `nombre`, `nit`, `estado`, `fecha_creacion`, `dias_restantes_trial`, `activo`, usuarios activos y tickets del mes.
4. WHEN el SUPER_ADMIN consulta `GET /talleres/{id}`, THE Sistema SHALL retornar el detalle completo incluyendo todos los campos de estado, configuración de localización y métricas completas.
5. WHEN el SUPER_ADMIN actualiza un Taller con `PATCH /talleres/{id}`, THE Sistema SHALL aplicar solo los campos presentes en el body (actualización parcial) y registrar en Audit_Log con `TALLER_UPDATE`.
6. IF se intenta crear un Taller con nombre duplicado, THEN THE Sistema SHALL retornar HTTP 409 con el mensaje "Ya existe un taller con ese nombre".
7. IF se accede a `GET /talleres/{id}` con ID inexistente, THEN THE Sistema SHALL retornar HTTP 404 con el mensaje "Taller no encontrado".

---

### Requisito 4: Onboarding de Nuevo Cliente

**User Story:** Como SUPER_ADMIN, quiero un flujo de onboarding estructurado para nuevos clientes, para que cada taller quede operativo antes de entregar acceso al Admin del taller.

#### Criterios de Aceptación

1. THE Sistema SHALL exponer `POST /talleres/{taller_id}/usuarios` protegido con `@require_role("SUPER_ADMIN")` para crear el primer usuario ADMIN de un taller.
2. WHEN el SUPER_ADMIN crea el primer Admin_Taller, THE Sistema SHALL asignar automáticamente el `taller_id` del path al nuevo usuario, sin aceptar `taller_id` en el body.
3. WHEN el SUPER_ADMIN crea el primer Admin_Taller, THE Sistema SHALL asignar rol `ADMIN` y registrar `USER_CREATE` en Audit_Log.
4. IF se intenta crear un usuario en un Taller con `estado = CANCELADO`, THEN THE Sistema SHALL retornar HTTP 400 con el mensaje "No se pueden crear usuarios en un taller cancelado".
5. WHEN el SUPER_ADMIN sube un logo mediante `POST /talleres/{taller_id}/logo`, THE Sistema SHALL almacenar el archivo en `uploads/logo/taller_{taller_id}/` y actualizar `logo_url` en `configuracion_taller`.
6. IF se sube un logo con formato distinto a `jpg`, `jpeg`, `png` o `webp`, THEN THE Sistema SHALL retornar HTTP 400 con el mensaje "Formato de imagen no permitido. Use jpg, jpeg, png o webp".

---

### Requisito 5: Dashboard de Métricas por Taller

**User Story:** Como SUPER_ADMIN, quiero ver métricas operativas de cada taller sin acceder a datos privados, para monitorear la salud de la plataforma.

#### Criterios de Aceptación

1. THE Sistema SHALL exponer `GET /talleres/{taller_id}/metricas` protegido con `@require_role("SUPER_ADMIN")`.
2. WHEN el SUPER_ADMIN consulta métricas de un Taller, THE Sistema SHALL retornar: `usuarios_activos`, `tickets_historicos`, `tickets_mes_actual`, `fecha_ultimo_acceso` (último LOGIN exitoso en Audit_Log del taller).
3. THE Sistema SHALL retornar únicamente conteos y timestamps, sin nombres de usuarios, contenido de tickets ni ningún dato privado.
4. IF se consultan métricas de un Taller inexistente, THEN THE Sistema SHALL retornar HTTP 404.

---

### Requisito 6: Dashboard de Métricas Globales

**User Story:** Como SUPER_ADMIN, quiero un resumen global de toda la plataforma en un solo endpoint.

#### Criterios de Aceptación

1. THE Sistema SHALL exponer `GET /admin/metricas` protegido con `@require_role("SUPER_ADMIN")`.
2. WHEN el SUPER_ADMIN consulta métricas globales, THE Sistema SHALL retornar: `total_talleres`, `talleres_por_estado` (counts por `TRIAL`, `ACTIVO`, `SUSPENDIDO`, `CANCELADO`), `total_usuarios_activos`, `total_usuarios`.
3. THE Sistema SHALL calcular las métricas globales con agregaciones SQL en una sola operación de base de datos.
4. THE Sistema SHALL retornar únicamente conteos agregados, sin datos identificables de talleres o usuarios individuales.

---

### Requisito 7: Control de Recursos por Taller

**User Story:** Como SUPER_ADMIN, quiero ver el consumo de recursos de cada taller para detectar uso excesivo.

#### Criterios de Aceptación

1. THE Sistema SHALL exponer `GET /talleres/{taller_id}/recursos` protegido con `@require_role("SUPER_ADMIN")`.
2. WHEN el SUPER_ADMIN consulta recursos de un Taller, THE Sistema SHALL retornar: `almacenamiento_bytes`, `almacenamiento_mb` (2 decimales), `tickets_mes_actual`, `limite_tickets_mes` (del plan, `null` si sin límite).
3. THE Sistema SHALL calcular `almacenamiento_bytes` recorriendo `uploads/taller_{taller_id}/` incluyendo todos los subdirectorios.
4. IF la ruta de almacenamiento no existe, THEN THE Sistema SHALL retornar `almacenamiento_bytes = 0` sin error.

---

### Requisito 8: Gestión de Usuarios por Taller

**User Story:** Como SUPER_ADMIN, quiero gestionar usuarios de cualquier taller para resolver emergencias de acceso.

#### Criterios de Aceptación

1. THE Sistema SHALL exponer `POST /talleres/{taller_id}/usuarios/{usuario_id}/reset-password` protegido con `@require_role("SUPER_ADMIN")` para forzar reset de contraseña de un usuario específico.
2. WHEN el SUPER_ADMIN fuerza reset de contraseña, THE Sistema SHALL invalidar todos los tokens JWT activos del usuario en `token_blacklist` y generar token de reset de un solo uso con expiración de 24 horas.
3. THE Sistema SHALL exponer `POST /talleres/{taller_id}/reset-passwords` protegido con `@require_role("SUPER_ADMIN")` para reset masivo de todos los usuarios del taller.
4. WHEN el SUPER_ADMIN fuerza reset masivo, THE Sistema SHALL invalidar todos los tokens JWT activos de todos los usuarios del taller.
5. THE Sistema SHALL registrar cada reset en Audit_Log con acción `PASSWORD_RESET` incluyendo el `taller_id` afectado.
6. IF se intenta resetear contraseña de un usuario que no pertenece al `taller_id` del path, THEN THE Sistema SHALL retornar HTTP 404 con el mensaje "Usuario no encontrado en este taller".

---

### Requisito 9: Bloqueo de Emergencia de Taller

**User Story:** Como SUPER_ADMIN, quiero bloquear un taller de forma inmediata ante una situación de seguridad, sin alterar su estado de suscripción ni borrar datos.

#### Criterios de Aceptación

1. THE Sistema SHALL extender la tabla `talleres` con: `bloqueado_emergencia` (boolean, NOT NULL, default `false`), `fecha_bloqueo_emergencia` (timestamp, nullable), `motivo_bloqueo_emergencia` (string, nullable).
2. THE Sistema SHALL exponer `POST /talleres/{taller_id}/bloqueo-emergencia` protegido con `@require_role("SUPER_ADMIN")`.
3. WHEN el SUPER_ADMIN activa el bloqueo de emergencia, THE Sistema SHALL establecer `bloqueado_emergencia = true`, registrar `fecha_bloqueo_emergencia = NOW()`, almacenar el motivo e invalidar todos los tokens JWT activos de todos los usuarios del taller.
4. WHILE un Taller tiene `bloqueado_emergencia = true`, THE AuthMiddleware SHALL rechazar requests de sus usuarios con HTTP 403 y mensaje "Taller bloqueado por razones de seguridad. Contacte al administrador de la plataforma.".
5. THE Sistema SHALL exponer `DELETE /talleres/{taller_id}/bloqueo-emergencia` protegido con `@require_role("SUPER_ADMIN")` para levantar el bloqueo.
6. WHEN el SUPER_ADMIN levanta el bloqueo, THE Sistema SHALL establecer `bloqueado_emergencia = false` y limpiar `fecha_bloqueo_emergencia` y `motivo_bloqueo_emergencia`.
7. THE Sistema SHALL registrar activación y levantamiento del bloqueo en Audit_Log con acción `SECURITY_ALERT`.
8. IF se intenta activar el bloqueo en un Taller ya bloqueado, THEN THE Sistema SHALL retornar HTTP 400 con el mensaje "El taller ya se encuentra bloqueado de emergencia".

---

### Requisito 10: Monitoreo de Seguridad por Taller

**User Story:** Como SUPER_ADMIN, quiero ver intentos de login fallidos por taller para detectar ataques de fuerza bruta.

#### Criterios de Aceptación

1. THE Sistema SHALL exponer `GET /talleres/{taller_id}/seguridad/intentos-fallidos` protegido con `@require_role("SUPER_ADMIN")`.
2. WHEN el SUPER_ADMIN consulta intentos fallidos, THE Sistema SHALL retornar registros del Audit_Log con acción `LOGIN_FAILED` filtrados por `taller_id`, ordenados por `timestamp` descendente, con paginación.
3. THE Sistema SHALL incluir en cada registro: `timestamp`, `ip_address`, `user_agent` y `username` del intento.
4. THE Sistema SHALL soportar parámetro de query `desde` (fecha ISO 8601) para filtrar por fecha.

---

### Requisito 11: Auditoría Cruzada Global

**User Story:** Como SUPER_ADMIN, quiero consultar el Audit_Log de toda la plataforma con filtros globales para investigar incidentes de seguridad.

#### Criterios de Aceptación

1. THE Sistema SHALL exponer `GET /admin/auditoria` protegido con `@require_role("SUPER_ADMIN")`.
2. WHEN el SUPER_ADMIN consulta auditoría global, THE Sistema SHALL soportar filtros opcionales: `taller_id`, `user_id`, `accion`, `desde`, `hasta`, `page`, `page_size`.
3. THE Sistema SHALL retornar registros ordenados por `timestamp` descendente con máximo 100 por página.
4. THE Sistema SHALL incluir en cada registro: `id`, `timestamp`, `taller_id`, `user_id`, `action`, `resource_type`, `resource_id`, `ip_address`, `details`.
5. IF `desde` es posterior a `hasta`, THEN THE Sistema SHALL retornar HTTP 400 con el mensaje "La fecha de inicio no puede ser posterior a la fecha de fin".


---

### Requisito 12: Organización de Uploads por Taller

**User Story:** Como desarrollador, quiero que todos los archivos subidos al sistema estén organizados por taller en carpetas separadas, para evitar colisiones de nombres y facilitar el control de almacenamiento por tenant.

#### Criterios de Aceptación

1. THE Sistema SHALL organizar todos los archivos subidos bajo la estructura `uploads/{tipo}/taller_{taller_id}/{archivo}` donde `tipo` puede ser: `logo`, `fotos`, `compras`, `firmas`, `pdfs`.
2. WHEN se sube una foto de ticket o proceso, THE Sistema SHALL almacenar el archivo en `uploads/fotos/taller_{taller_id}/` en lugar de `uploads/fotos/`.
3. WHEN se sube un soporte de compra, THE Sistema SHALL almacenar el archivo en `uploads/compras/taller_{taller_id}/` en lugar de `uploads/compras/`.
4. WHEN se sube un logo de taller, THE Sistema SHALL almacenar el archivo en `uploads/logo/taller_{taller_id}/` en lugar de `uploads/logo/`.
5. WHEN se genera un PDF de ticket, THE Sistema SHALL almacenar el archivo en `uploads/pdfs/taller_{taller_id}/` si se persiste en disco.
6. THE Sistema SHALL crear automáticamente la carpeta del taller si no existe al momento de subir el primer archivo.
7. THE Sistema SHALL usar el `taller_id` del `request.state.taller_id` para determinar la carpeta destino, nunca un valor del body o query params.

---

### Requisito 13: Script SQL de Creación del SUPER_ADMIN

**User Story:** Como desarrollador de la plataforma, quiero un script SQL documentado y seguro para crear el SUPER_ADMIN, para que el bootstrap de la plataforma sea reproducible sin exponer superficie de ataque HTTP.

#### Criterios de Aceptación

1. THE Sistema SHALL proveer el archivo `scripts/crear_super_admin.sql` con las sentencias SQL para crear el usuario SUPER_ADMIN directamente en la base de datos.
2. THE Script SHALL insertar el usuario en `users` con `taller_id = NULL`, `is_active = true` y `password_hash` generado con bcrypt (costo 12).
3. THE Script SHALL insertar o referenciar el rol `SUPER_ADMIN` en `roles` y crear la asociación en `user_roles`.
4. THE Script SHALL ser idempotente: si el SUPER_ADMIN ya existe, actualiza la contraseña sin crear duplicados usando `ON CONFLICT DO UPDATE`.
5. THE Script SHALL incluir al inicio un bloque de comentarios que documente: propósito del script, instrucción de cambiar la contraseña por defecto antes de producción, y advertencia de que es el único método autorizado para crear un SUPER_ADMIN.
6. THE Script SHALL incluir instrucciones de uso en los comentarios: `psql -U postgres -d taller_v3 -f scripts/crear_super_admin.sql`.
7. IF el script se ejecuta en una BD donde la tabla `users` no existe, THEN THE Script SHALL fallar con un mensaje de error claro sin dejar la BD en estado inconsistente.

---

### Requisito 14: Campos de Estado y Localización en Modelos SQLAlchemy

**User Story:** Como desarrollador, quiero que los modelos SQLAlchemy y la BD `taller_v3` reflejen todos los campos nuevos acordados, para que el código y la base de datos estén sincronizados desde el inicio.

#### Criterios de Aceptación

1. THE Sistema SHALL agregar a la tabla `talleres` y al modelo `Taller` los campos: `estado` (enum: `TRIAL`, `ACTIVO`, `SUSPENDIDO`, `CANCELADO`, default `TRIAL`), `fecha_inicio_trial` (timestamp, nullable), `dias_trial` (integer, nullable), `fecha_suspension` (timestamp, nullable), `fecha_cancelacion` (timestamp, nullable), `bloqueado_emergencia` (boolean, default false), `fecha_bloqueo_emergencia` (timestamp, nullable), `motivo_bloqueo_emergencia` (string, nullable).
2. THE Sistema SHALL agregar a la tabla `configuracion_taller` y al modelo `ConfiguracionTaller` los campos: `moneda` (string 3, default `COP`), `idioma` (string 2, default `es`), `timezone` (string, default `America/Bogota`).
3. THE Sistema SHALL crear una migración Alembic que agregue todos los campos del criterio 1 y 2 a la BD `taller_v3` existente.
4. THE Sistema SHALL actualizar el script `db/setup_v3_completo.sql` para incluir todos los campos nuevos, de modo que una instalación desde cero ya los tenga.
5. THE Sistema SHALL agregar al enum `AuditAction` las nuevas acciones: `TALLER_ACTIVATE`, `TALLER_SUSPEND`, `TALLER_CANCEL`, `PLAN_ASIGNADO`, `PAGO_REGISTRADO`, `NOTIFICACION_ENVIADA`.
