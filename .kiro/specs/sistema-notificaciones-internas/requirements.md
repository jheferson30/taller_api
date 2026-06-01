# Documento de Requisitos: Sistema de Notificaciones Internas

## Introducción

Este documento describe los requisitos para el sistema de notificaciones internas de la plataforma SaaS de gestión de talleres mecánicos.

Las notificaciones internas son mensajes que se muestran dentro de la aplicación (no por email ni WhatsApp). Hay dos tipos de emisores: el **SUPER_ADMIN** (que envía anuncios a talleres) y el **sistema automático** (que notifica al ADMIN del taller sobre límites, vencimientos y eventos de seguridad).

---

## Glosario

- **Notificacion_Interna**: Mensaje mostrado dentro de la app al usuario destinatario.
- **Notificacion_Plataforma**: Notificación enviada por el SUPER_ADMIN a uno o todos los talleres.
- **Notificacion_Sistema**: Notificación generada automáticamente por el sistema (límites, vencimientos, seguridad).
- **Destinatario**: Usuario que recibe la notificación. Puede ser el ADMIN de un taller o todos los ADMINs.
- **Historial_Mensajes**: Registro persistente de todas las notificaciones enviadas.

---

## Requisitos

### Requisito 1: Modelo de Datos de Notificaciones

**User Story:** Como desarrollador, quiero un modelo de datos robusto para notificaciones internas, para que el sistema pueda almacenar y recuperar notificaciones de forma eficiente.

#### Criterios de Aceptación

1. THE Sistema SHALL crear la tabla `notificaciones_internas` con los campos: `id` (PK), `taller_id` (FK → `talleres.id`, nullable — null = global para todos los talleres), `user_id` (FK → `users.id`, nullable — null = para todos los usuarios del taller), `titulo` (string 200, NOT NULL), `mensaje` (text, NOT NULL), `tipo` (enum: `INFO`, `ADVERTENCIA`, `URGENTE`, `MANTENIMIENTO`, `LIMITE_PLAN`, `VENCIMIENTO`, `SEGURIDAD`), `leida` (boolean, default false), `fecha_creacion` (timestamp, NOT NULL), `creado_por` (FK → `users.id`, nullable — null si es generada por el sistema).
2. THE Sistema SHALL crear índices en `notificaciones_internas` sobre: `taller_id`, `user_id`, `leida`, `fecha_creacion`.
3. THE Sistema SHALL soportar notificaciones globales (`taller_id = null`) que son visibles para todos los talleres.
4. THE Sistema SHALL soportar notificaciones por taller (`taller_id = X`, `user_id = null`) visibles para todos los usuarios del taller.
5. THE Sistema SHALL soportar notificaciones por usuario (`taller_id = X`, `user_id = Y`) visibles solo para ese usuario.

---

### Requisito 2: Envío de Notificaciones por el SUPER_ADMIN

**User Story:** Como SUPER_ADMIN, quiero enviar notificaciones o anuncios a uno o todos los talleres, para comunicar mantenimientos, actualizaciones o alertas importantes.

#### Criterios de Aceptación

1. THE Sistema SHALL exponer `POST /admin/notificaciones` protegido con `@require_role("SUPER_ADMIN")` para enviar una notificación.
2. WHEN el SUPER_ADMIN envía una notificación con `taller_id = null`, THE Sistema SHALL crear un único registro con `taller_id = null` que representa un mensaje global visible para todos los talleres.
3. WHEN el SUPER_ADMIN envía una notificación con un `taller_id` específico, THE Sistema SHALL crear un registro dirigido solo a ese taller.
4. THE Sistema SHALL validar que el `tipo` de la notificación sea uno de: `INFO`, `ADVERTENCIA`, `URGENTE`, `MANTENIMIENTO`.
5. IF se envía una notificación a un `taller_id` inexistente, THEN THE Sistema SHALL retornar HTTP 404 con el mensaje "Taller no encontrado".
6. THE Sistema SHALL registrar en Audit_Log el envío de cada notificación con acción `NOTIFICACION_ENVIADA`.

---

### Requisito 3: Notificaciones Automáticas del Sistema

**User Story:** Como ADMIN del taller, quiero recibir notificaciones automáticas sobre eventos importantes de mi taller, para estar informado sin tener que consultar manualmente.

#### Criterios de Aceptación

1. THE Sistema SHALL generar notificaciones automáticas con `creado_por = null` (generadas por el sistema) para los siguientes eventos: límite de plan al 80%, límite de plan al 100%, vencimiento a 7 días, vencimiento a 3 días, vencimiento a 1 día, suspensión automática del taller, bloqueo de emergencia.
2. WHEN el sistema genera una notificación automática, THE Sistema SHALL asignar `user_id` al ADMIN activo del taller (usuario con rol `ADMIN` e `is_active = true`).
3. IF un taller tiene múltiples usuarios con rol `ADMIN`, THEN THE Sistema SHALL enviar la notificación a todos los ADMINs activos del taller.
4. THE Sistema SHALL asignar el tipo correcto a cada notificación automática: `LIMITE_PLAN` para límites, `VENCIMIENTO` para vencimientos, `SEGURIDAD` para bloqueos.

---

### Requisito 4: Consulta de Notificaciones por el Usuario

**User Story:** Como usuario autenticado, quiero ver mis notificaciones pendientes dentro de la app, para estar al tanto de eventos importantes de mi taller.

#### Criterios de Aceptación

1. THE Sistema SHALL exponer `GET /notificaciones` protegido con `@require_auth` que retorne las notificaciones del usuario autenticado.
2. WHEN un usuario consulta sus notificaciones, THE Sistema SHALL retornar: notificaciones globales (`taller_id = null`), notificaciones del taller del usuario (`taller_id = user.taller_id`, `user_id = null`), y notificaciones específicas del usuario (`user_id = user.id`).
3. THE Sistema SHALL retornar las notificaciones ordenadas por `fecha_creacion` descendente con paginación.
4. THE Sistema SHALL incluir en cada notificación: `id`, `titulo`, `mensaje`, `tipo`, `leida`, `fecha_creacion`.
5. THE Sistema SHALL exponer `GET /notificaciones/no-leidas/count` protegido con `@require_auth` que retorne el conteo de notificaciones no leídas del usuario.

---

### Requisito 5: Marcar Notificaciones como Leídas

**User Story:** Como usuario autenticado, quiero marcar notificaciones como leídas, para mantener limpio mi panel de notificaciones.

#### Criterios de Aceptación

1. THE Sistema SHALL exponer `PATCH /notificaciones/{id}/leer` protegido con `@require_auth` para marcar una notificación como leída.
2. WHEN un usuario marca una notificación como leída, THE Sistema SHALL establecer `leida = true` solo si la notificación pertenece al usuario, a su taller o es global.
3. THE Sistema SHALL exponer `PATCH /notificaciones/leer-todas` protegido con `@require_auth` para marcar todas las notificaciones del usuario como leídas.
4. IF un usuario intenta marcar como leída una notificación que no le corresponde, THEN THE Sistema SHALL retornar HTTP 404 con el mensaje "Notificación no encontrada".

---

### Requisito 6: Historial de Notificaciones para el SUPER_ADMIN

**User Story:** Como SUPER_ADMIN, quiero ver el historial completo de notificaciones enviadas, para auditar las comunicaciones con los talleres.

#### Criterios de Aceptación

1. THE Sistema SHALL exponer `GET /admin/notificaciones` protegido con `@require_role("SUPER_ADMIN")` que retorne el Historial_Mensajes completo con paginación.
2. WHEN el SUPER_ADMIN consulta el historial, THE Sistema SHALL soportar filtros opcionales: `taller_id`, `tipo`, `desde`, `hasta`.
3. THE Sistema SHALL incluir en cada registro del historial: `id`, `taller_id`, `titulo`, `tipo`, `fecha_creacion`, `creado_por` (nombre del SUPER_ADMIN o "Sistema").
4. THE Sistema SHALL exponer `GET /talleres/{taller_id}/notificaciones` protegido con `@require_role("SUPER_ADMIN")` que retorne las notificaciones de un taller específico más las globales.
