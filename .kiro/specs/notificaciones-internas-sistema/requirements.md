# Documento de Requisitos

## Introducción

Este documento especifica los requisitos para el sistema de **notificaciones internas** del SaaS de gestión de talleres mecánicos. Se cubren dos funcionalidades:

1. **Asignación de ticket a mecánico con notificación interna**: al crear o actualizar un ticket, el ADMIN puede asignar el trabajo a un mecánico específico. El mecánico asignado recibe una notificación interna no invasiva (badge/contador) visible en la UI.

2. **Alerta de renovación del plan SaaS**: cuando faltan 3 días o menos para el vencimiento del plan mensual del taller, el ADMIN ve una notificación interna no invasiva (banner o badge) en la aplicación.

Ambas funcionalidades comparten la misma infraestructura de notificaciones internas: un modelo `Notificacion` en base de datos, endpoints REST para consultar y marcar como leídas, y un componente de UI que muestra el contador/badge sin interrumpir el flujo de trabajo.

---

## Glosario

- **Sistema**: el backend FastAPI del SaaS de gestión de talleres mecánicos.
- **Frontend**: la aplicación React que consume la API.
- **Notificacion**: registro persistente en base de datos que representa un aviso interno dirigido a un usuario específico dentro de un taller.
- **Badge**: indicador visual numérico (ej. "3") superpuesto sobre un ícono en la UI que muestra la cantidad de notificaciones no leídas.
- **Banner**: franja informativa no bloqueante que aparece en la parte superior o inferior de la pantalla.
- **Ticket**: orden de trabajo de un vehículo en el taller.
- **Mecanico**: técnico del taller registrado en la tabla `mecanicos`, identificado por `mecanico_id`.
- **ADMIN**: usuario con rol `ADMIN` dentro de un taller.
- **MECANICO_USER**: usuario con rol `MECANICO` dentro de un taller, vinculado a un registro `Mecanico`.
- **Taller**: tenant del sistema, identificado por `taller_id` en el JWT.
- **Plan**: suscripción mensual del taller con fecha de vencimiento almacenada en el modelo `Taller`.
- **Repositorio_Notificacion**: capa de acceso a datos para la entidad `Notificacion`.
- **Servicio_Notificacion**: capa de lógica de negocio que crea, consulta y gestiona notificaciones.
- **Servicio_Ticket**: capa de lógica de negocio existente para tickets, que se extiende para soportar asignación.
- **Verificador_Plan**: componente del `Servicio_Notificacion` que evalúa la proximidad del vencimiento del plan.

---

## Requisitos

### Requisito 1: Modelo de datos de notificaciones internas

**User Story:** Como desarrollador, quiero un modelo de datos persistente para notificaciones internas, para que las notificaciones sobrevivan recargas de página y puedan consultarse en cualquier momento.

#### Criterios de Aceptación

1. THE `Sistema` SHALL almacenar cada notificación con los campos: `id`, `taller_id`, `destinatario_user_id`, `tipo` (enum: `TICKET_ASIGNADO`, `RENOVACION_PLAN`), `titulo`, `mensaje`, `leida` (booleano, default `false`), `fecha_creacion`, `referencia_id` (entero nullable, para vincular al ticket o al taller).
2. THE `Sistema` SHALL garantizar que el campo `taller_id` en `Notificacion` sea siempre igual al `taller_id` del usuario destinatario, como invariante de aislamiento multi-tenant.
3. WHEN una notificación es creada, THE `Sistema` SHALL asignar `leida = false` por defecto.
4. THE `Repositorio_Notificacion` SHALL filtrar siempre por `taller_id` en toda consulta, sin excepción.

---

### Requisito 2: Asignación de ticket a mecánico

**User Story:** Como ADMIN del taller, quiero asignar un ticket a un mecánico específico al crearlo o actualizarlo, para que el mecánico sepa qué trabajo debe realizar.

#### Criterios de Aceptación

1. THE `Sistema` SHALL agregar el campo `mecanico_asignado_id` (FK a `mecanicos.id`, nullable) al modelo `Ticket`.
2. WHEN el ADMIN crea un ticket con `mecanico_asignado_id` presente, THE `Servicio_Ticket` SHALL verificar que el mecánico pertenezca al mismo `taller_id` del token JWT antes de persistir la asignación.
3. WHEN el ADMIN actualiza un ticket con un nuevo `mecanico_asignado_id`, THE `Servicio_Ticket` SHALL verificar que el mecánico pertenezca al mismo `taller_id` del token JWT antes de persistir el cambio.
4. IF el `mecanico_asignado_id` no pertenece al `taller_id` del token JWT, THEN THE `Sistema` SHALL retornar HTTP 404 sin revelar la existencia del mecánico en otro taller.
5. THE `Sistema` SHALL mantener el campo `recepcionado_por` (texto libre) independiente y sin modificaciones al agregar `mecanico_asignado_id`.

---

### Requisito 3: Notificación interna al asignar ticket

**User Story:** Como mecánico, quiero recibir una notificación interna cuando me asignan un ticket, para enterarme sin que se interrumpa mi flujo de trabajo.

#### Criterios de Aceptación

1. WHEN un ticket es creado o actualizado con un `mecanico_asignado_id` válido, THE `Servicio_Notificacion` SHALL crear una `Notificacion` de tipo `TICKET_ASIGNADO` dirigida al `user_id` del mecánico asignado.
2. WHEN el `mecanico_asignado_id` de un ticket cambia a un mecánico diferente, THE `Servicio_Notificacion` SHALL crear una nueva notificación para el nuevo mecánico asignado.
3. WHEN el `mecanico_asignado_id` de un ticket no cambia en una actualización, THE `Servicio_Notificacion` SHALL omitir la creación de una notificación duplicada.
4. THE `Notificacion` de tipo `TICKET_ASIGNADO` SHALL incluir en `referencia_id` el `id` del ticket al que hace referencia.
5. IF el mecánico asignado no tiene un `user_id` vinculado en el sistema, THEN THE `Servicio_Notificacion` SHALL omitir la creación de la notificación sin lanzar error, registrando el evento en el log de aplicación.

---

### Requisito 4: Consulta de notificaciones no leídas

**User Story:** Como usuario autenticado (ADMIN o MECANICO), quiero consultar mis notificaciones no leídas, para saber cuántas tengo y cuáles son.

#### Criterios de Aceptación

1. WHEN un usuario autenticado consulta `GET /notificaciones/no-leidas`, THE `Sistema` SHALL retornar únicamente las notificaciones con `leida = false` que pertenezcan al `taller_id` y `user_id` del token JWT.
2. THE `Sistema` SHALL retornar el conteo total de notificaciones no leídas junto con la lista de notificaciones en la misma respuesta.
3. WHILE el usuario tiene sesión activa, THE `Frontend` SHALL consultar el endpoint de notificaciones no leídas con un intervalo de 30 segundos para mantener el badge actualizado.
4. THE `Sistema` SHALL responder el endpoint `GET /notificaciones/no-leidas` en menos de 300ms bajo carga normal.
5. IF el token JWT no contiene un `user_id` válido, THEN THE `Sistema` SHALL retornar HTTP 401.

---

### Requisito 5: Marcar notificaciones como leídas

**User Story:** Como usuario autenticado, quiero marcar notificaciones como leídas, para que el badge refleje solo las pendientes reales.

#### Criterios de Aceptación

1. WHEN un usuario autenticado envía `PATCH /notificaciones/{id}/leer`, THE `Sistema` SHALL marcar la notificación como `leida = true` solo si `notificacion.taller_id == taller_id del JWT` y `notificacion.destinatario_user_id == user_id del JWT`.
2. IF la notificación no pertenece al usuario autenticado o al taller del JWT, THEN THE `Sistema` SHALL retornar HTTP 404 sin revelar la existencia de la notificación.
3. WHEN un usuario autenticado envía `PATCH /notificaciones/leer-todas`, THE `Sistema` SHALL marcar como `leida = true` todas las notificaciones no leídas del `user_id` y `taller_id` del JWT.
4. THE `Sistema` SHALL garantizar que un usuario no pueda marcar como leída una notificación de otro usuario, incluso dentro del mismo taller.

---

### Requisito 6: Badge de notificaciones en la UI

**User Story:** Como usuario autenticado, quiero ver un badge con el conteo de notificaciones no leídas en la barra de navegación, para estar informado sin interrupciones.

#### Criterios de Aceptación

1. WHEN el conteo de notificaciones no leídas es mayor a cero, THE `Frontend` SHALL mostrar un badge numérico sobre el ícono de notificaciones en la barra de navegación.
2. WHEN el conteo de notificaciones no leídas es cero, THE `Frontend` SHALL ocultar el badge.
3. THE `Frontend` SHALL actualizar el badge automáticamente tras marcar una o todas las notificaciones como leídas, sin recargar la página.
4. THE `Frontend` SHALL mostrar el badge de forma no invasiva: sin modales bloqueantes, sin sonidos, sin interrupciones al flujo de trabajo activo.
5. WHERE el usuario tiene rol `MECANICO`, THE `Frontend` SHALL mostrar en la vista principal la lista de tickets asignados pendientes (estado `ABIERTO` o `EN_PROCESO`) al iniciar sesión.

---

### Requisito 7: Alerta de renovación del plan SaaS

**User Story:** Como ADMIN del taller, quiero recibir una notificación interna cuando el plan está próximo a vencer, para renovarlo a tiempo y evitar la suspensión del servicio.

#### Criterios de Aceptación

1. WHEN el `Verificador_Plan` evalúa un taller y la diferencia entre `fecha_vencimiento_plan` y la fecha actual es menor o igual a 3 días, THE `Servicio_Notificacion` SHALL crear una `Notificacion` de tipo `RENOVACION_PLAN` dirigida a todos los usuarios con rol `ADMIN` del taller.
2. WHEN el `Verificador_Plan` ya creó una notificación de tipo `RENOVACION_PLAN` para un taller en las últimas 24 horas, THE `Servicio_Notificacion` SHALL omitir la creación de una notificación duplicada para ese taller.
3. THE `Verificador_Plan` SHALL ejecutarse como tarea programada una vez por día.
4. IF el taller tiene estado `SUSPENDIDO` o `CANCELADO`, THEN THE `Verificador_Plan` SHALL omitir la evaluación de ese taller.
5. IF el taller no tiene `fecha_vencimiento_plan` definida (valor null), THEN THE `Verificador_Plan` SHALL omitir la evaluación de ese taller sin lanzar error.
6. THE `Notificacion` de tipo `RENOVACION_PLAN` SHALL incluir en `mensaje` la cantidad exacta de días restantes hasta el vencimiento.

---

### Requisito 8: Visualización de la alerta de renovación en la UI

**User Story:** Como ADMIN del taller, quiero ver la alerta de renovación de forma discreta en la UI, para no interrumpir mi trabajo mientras gestiono el taller.

#### Criterios de Aceptación

1. WHEN el ADMIN tiene una notificación no leída de tipo `RENOVACION_PLAN`, THE `Frontend` SHALL mostrar un banner informativo no bloqueante en la parte superior de la pantalla con el mensaje de vencimiento.
2. THE `Frontend` SHALL permitir al ADMIN cerrar el banner manualmente, lo que marcará la notificación como leída.
3. THE `Frontend` SHALL mostrar el banner de renovación únicamente a usuarios con rol `ADMIN`, nunca a usuarios con rol `MECANICO`.
4. WHEN el ADMIN marca la notificación de renovación como leída, THE `Frontend` SHALL ocultar el banner sin recargar la página.

---

### Requisito 9: Seguridad y aislamiento multi-tenant de notificaciones

**User Story:** Como operador del sistema, quiero que las notificaciones estén completamente aisladas por taller, para que ningún usuario pueda ver ni manipular notificaciones de otro taller.

#### Criterios de Aceptación

1. THE `Sistema` SHALL proteger todos los endpoints de notificaciones con `@require_auth`, rechazando requests sin JWT válido con HTTP 401.
2. THE `Repositorio_Notificacion` SHALL incluir el filtro `taller_id == taller_id del JWT` en toda operación de lectura y escritura, sin excepción.
3. IF un usuario intenta acceder a una notificación de otro taller, THEN THE `Sistema` SHALL retornar HTTP 404, nunca HTTP 403, para no revelar la existencia del recurso.
4. THE `Sistema` SHALL obtener el `taller_id` exclusivamente del token JWT en todos los endpoints de notificaciones, nunca del body, query params ni headers del cliente.
5. THE `Sistema` SHALL registrar en el audit log la creación de notificaciones de tipo `RENOVACION_PLAN` para trazabilidad.
