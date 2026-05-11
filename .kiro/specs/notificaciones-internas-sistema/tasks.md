# Plan de Implementación: Sistema de Notificaciones Internas

## Visión General

Implementar la infraestructura completa de notificaciones internas: modelo de datos, repositorio multi-tenant, servicio de negocio, extensión de TicketService, endpoints REST, tarea Celery Beat y componentes React (badge + banner).

## Tareas

- [x] 1. Migración Alembic y modelos de datos
  - [x] 1.1 Crear modelo `Notificacion` con enum `TipoNotificacion`
    - Crear `app/modelos/notificacion.py` con `TipoNotificacion(StrEnum)` y clase `Notificacion(Base)`
    - Campos: `id`, `taller_id` (FK talleres), `destinatario_user_id` (FK users), `tipo`, `titulo`, `mensaje`, `leida` (default False), `fecha_creacion`, `referencia_id`
    - Agregar `Notificacion` al `__init__.py` de modelos
    - _Requisitos: 1.1, 1.3_

  - [x] 1.2 Extender modelos `Ticket` y `Taller`
    - Agregar `mecanico_asignado_id = Column(Integer, ForeignKey("mecanicos.id"), nullable=True, index=True)` en `app/modelos/ticket.py`
    - Agregar `fecha_vencimiento_plan = Column(DateTime(timezone=True), nullable=True)` en `app/modelos/taller.py` si no existe
    - _Requisitos: 2.1_

  - [x] 1.3 Crear migración Alembic
    - Generar `migrations/versions/XXXX_add_notificaciones_mecanico_asignado.py`
    - `upgrade()`: agregar `mecanico_asignado_id` a tickets, `fecha_vencimiento_plan` a talleres, crear tabla `notificaciones` con todos sus índices incluyendo el compuesto `ix_notificaciones_tenant_user_leida`
    - `downgrade()`: revertir en orden inverso, eliminar enum `tiponotificacion`
    - _Requisitos: 1.1, 2.1_

- [x] 2. Schemas Pydantic
  - [x] 2.1 Crear `app/esquemas/notificacion_schema.py`
    - Definir `NotificacionRespuesta` con `id`, `tipo`, `titulo`, `mensaje`, `leida`, `fecha_creacion`, `referencia_id`; `model_config = ConfigDict(from_attributes=True)`
    - Definir `NotificacionesNoLeidasRespuesta` con `total: int` y `notificaciones: list[NotificacionRespuesta]`
    - _Requisitos: 4.1, 4.2_

- [x] 3. Repositorio multi-tenant
  - [x] 3.1 Crear `app/repositorios/notificacion_repository.py`
    - Extender `TenantRepository`; el constructor recibe `db` y `taller_id`
    - `get_no_leidas(user_id) → list[Notificacion]`: filtra por `taller_id`, `destinatario_user_id`, `leida=False`
    - `get_by_id_y_usuario(notif_id, user_id) → Notificacion | None`: filtra por `id`, `taller_id`, `destinatario_user_id`
    - `marcar_leida(notif_id, user_id) → bool`: actualiza solo si pertenece al usuario y taller
    - `marcar_todas_leidas(user_id) → int`: retorna cantidad actualizada
    - `existe_notif_renovacion_reciente(taller_id, horas=24) → bool`: verifica si ya existe `RENOVACION_PLAN` en las últimas N horas
    - Todo método incluye filtro `taller_id` sin excepción
    - _Requisitos: 1.4, 9.2, 9.4_

  - [x] 3.2 Escribir test de propiedad: aislamiento multi-tenant del repositorio
    - **Propiedad 1: Aislamiento multi-tenant del repositorio**
    - **Valida: Requisitos 1.4, 9.2**
    - Usar `@given(st.lists(notificacion_strategy(), min_size=2))` con notificaciones de talleres distintos
    - Verificar que `get_no_leidas` nunca retorna notificaciones de otro `taller_id`

  - [x] 3.3 Escribir test de propiedad: invariante de tenant en notificación creada
    - **Propiedad 2: Invariante de tenant en notificación creada**
    - **Valida: Requisitos 1.2**
    - Verificar que `taller_id` de la notificación siempre coincide con el `taller_id` del destinatario

  - [x] 3.4 Escribir test de propiedad: estado inicial de notificación
    - **Propiedad 3: Estado inicial de notificación**
    - **Valida: Requisitos 1.3**
    - Verificar que toda notificación recién creada tiene `leida = False`

- [x] 4. Servicio de notificaciones
  - [x] 4.1 Crear `app/servicios/notificacion_service.py`
    - Constructor recibe `db` y `taller_id` (del JWT)
    - `obtener_no_leidas(user_id) → dict`: llama al repositorio y retorna `{"total": N, "notificaciones": [...]}`
    - `marcar_como_leida(notif_id, user_id) → Notificacion`: lanza HTTP 404 si no pertenece al usuario/taller
    - `marcar_todas_como_leidas(user_id) → int`: retorna cantidad marcada
    - `crear_notificacion_asignacion(ticket, mecanico_user_id) → Notificacion | None`: crea `TICKET_ASIGNADO`; si `mecanico_user_id` es None, loguea advertencia y retorna None sin lanzar error
    - `crear_notificaciones_renovacion(taller, admins, dias_restantes) → list[Notificacion]`: crea `RENOVACION_PLAN` para cada admin con mensaje que incluye días exactos
    - _Requisitos: 3.1, 3.4, 3.5, 4.1, 4.2, 5.1, 5.2, 5.3, 7.1, 7.6_

  - [x] 4.2 Escribir test de propiedad: notificación generada al asignar mecánico
    - **Propiedad 6: Notificación generada al asignar mecánico**
    - **Valida: Requisitos 3.1, 3.4**
    - Verificar que existe exactamente una `TICKET_ASIGNADO` con `referencia_id == ticket.id` para el `user_id` del mecánico

  - [x] 4.3 Escribir test de propiedad: idempotencia de notificación de asignación
    - **Propiedad 7: Idempotencia de notificación de asignación**
    - **Valida: Requisitos 3.3**
    - Verificar que si `mecanico_asignado_id` no cambia, el total de notificaciones `TICKET_ASIGNADO` no aumenta

  - [x] 4.4 Escribir test de propiedad: aislamiento de consulta de no leídas
    - **Propiedad 8: Aislamiento de consulta de notificaciones no leídas**
    - **Valida: Requisitos 4.1, 4.2**
    - Verificar que el resultado solo contiene notificaciones del `user_id` y `taller_id` del JWT, y que `total == len(notificaciones)`

  - [x] 4.5 Escribir test de propiedad: aislamiento de escritura al marcar como leída
    - **Propiedad 9: Aislamiento de escritura al marcar como leída**
    - **Valida: Requisitos 5.1, 5.2, 5.4**
    - Verificar que marcar como leída una notificación de otro usuario/taller retorna HTTP 404 sin modificar estado

  - [x] 4.6 Escribir test de propiedad: leer-todas marca exactamente las del usuario
    - **Propiedad 10: Leer-todas marca exactamente las notificaciones del usuario**
    - **Valida: Requisitos 5.3**
    - Verificar que tras `marcar_todas_como_leidas`, el usuario tiene 0 no leídas y las notificaciones de otros usuarios del mismo taller no cambian

- [x] 5. Extensión de TicketService
  - [x] 5.1 Agregar método `asignar_mecanico` en `app/servicios/ticket_service.py`
    - Verificar que `mecanico.taller_id == taller_id` del servicio; si no coincide, lanzar HTTP 404
    - Detectar si `mecanico_asignado_id` cambió respecto al valor anterior del ticket
    - Llamar a `NotificacionService.crear_notificacion_asignacion` solo si cambió
    - Integrar la llamada dentro de `crear_ticket` y `actualizar_ticket` usando `db.begin_nested()` para atomicidad (ticket + notificación en la misma transacción)
    - _Requisitos: 2.2, 2.3, 2.4, 2.5, 3.2, 3.3_

  - [x] 5.2 Escribir test de propiedad: aislamiento de asignación de mecánico
    - **Propiedad 4: Aislamiento de asignación de mecánico**
    - **Valida: Requisitos 2.2, 2.3, 2.4**
    - Verificar que asignar un mecánico de otro taller retorna HTTP 404 y el ticket no es modificado

  - [x] 5.3 Escribir test de propiedad: no interferencia de campos en Ticket
    - **Propiedad 5: No interferencia de campos en Ticket**
    - **Valida: Requisitos 2.5**
    - Verificar que asignar/cambiar `mecanico_asignado_id` no modifica `recepcionado_por`

- [x] 6. Checkpoint — Verificar capa de datos y servicios
  - Ejecutar tests de propiedades 1–10 y tests de ejemplo del repositorio y servicio
  - Verificar que la migración aplica sin errores con `alembic upgrade head`
  - Asegurarse de que todos los tests pasen antes de continuar

- [x] 7. Endpoints REST
  - [x] 7.1 Crear `app/rutas/notificacion_ruta.py`
    - `GET /notificaciones/no-leidas`: protegido con `@require_auth` y `@require_role("ADMIN", "MECANICO")`; obtiene `user_id` y `taller_id` del JWT; retorna `NotificacionesNoLeidasRespuesta`
    - `PATCH /notificaciones/{id}/leer`: protegido con `@require_auth` y `@require_role("ADMIN", "MECANICO")`; retorna `NotificacionRespuesta`; HTTP 404 si no pertenece al usuario/taller
    - `PATCH /notificaciones/leer-todas`: protegido con `@require_auth` y `@require_role("ADMIN", "MECANICO")`; retorna `{"marcadas": N}`
    - Rechazar tokens con `taller_id = null` (SUPER_ADMIN) con HTTP 403
    - `taller_id` obtenido exclusivamente del JWT, nunca del body ni query params
    - _Requisitos: 4.1, 4.2, 4.5, 5.1, 5.2, 5.3, 9.1, 9.3, 9.4_

  - [x] 7.2 Registrar router en `app/main.py`
    - Incluir `notificacion_router` con prefijo `/notificaciones`
    - _Requisitos: 4.1_

  - [x] 7.3 Escribir tests de ejemplo para los endpoints
    - Test: endpoint sin JWT retorna 401 (Req 4.5, 9.1)
    - Test: SUPER_ADMIN (taller_id=null) retorna 403
    - Test: usuario obtiene solo sus notificaciones no leídas
    - Test: marcar notificación de otro usuario retorna 404

- [x] 8. Tarea Celery Beat — Verificador de plan
  - [x] 8.1 Crear `app/tasks/notificacion_tasks.py`
    - Tarea `verificar_vencimientos_plan` decorada con `@celery_app.task`
    - Consultar talleres con estado `ACTIVO` o `TRIAL` y `fecha_vencimiento_plan IS NOT NULL`
    - Para cada taller: calcular días restantes; si `dias_restantes <= 3` y no existe notificación reciente (< 24h), obtener usuarios con rol `ADMIN` del taller y llamar a `NotificacionService.crear_notificaciones_renovacion`
    - Omitir talleres con estado `SUSPENDIDO` o `CANCELADO`
    - Omitir talleres sin `fecha_vencimiento_plan`
    - Registrar en audit log la creación de notificaciones `RENOVACION_PLAN`
    - Manejo de errores: log de error por taller fallido, continuar con el siguiente
    - _Requisitos: 7.1, 7.2, 7.3, 7.4, 7.5, 9.5_

  - [x] 8.2 Registrar tarea en `app/tasks/celery_app.py`
    - Agregar `beat_schedule` con `verificar_vencimientos_plan` programada diariamente (crontab `hour=0, minute=0`)
    - _Requisitos: 7.3_

  - [x] 8.3 Escribir test de propiedad: verificador genera notificación cuando corresponde
    - **Propiedad 11: Verificador de plan genera notificación cuando corresponde**
    - **Valida: Requisitos 7.1, 7.6**
    - Verificar que para talleres ACTIVO/TRIAL con `dias_restantes <= 3`, se crean notificaciones para todos los ADMIN y el mensaje contiene el número exacto de días

  - [x] 8.4 Escribir test de propiedad: idempotencia del verificador de plan
    - **Propiedad 12: Idempotencia del verificador de plan**
    - **Valida: Requisitos 7.2**
    - Verificar que si ya existe una `RENOVACION_PLAN` en las últimas 24h, no se crean notificaciones adicionales

  - [x] 8.5 Escribir test de propiedad: verificador omite talleres suspendidos o cancelados
    - **Propiedad 13: Verificador omite talleres suspendidos o cancelados**
    - **Valida: Requisitos 7.4**
    - Verificar que talleres con estado `SUSPENDIDO` o `CANCELADO` no generan ninguna notificación

- [x] 9. Checkpoint — Verificar backend completo
  - Ejecutar todos los tests de propiedades y de ejemplo del backend
  - Verificar que los endpoints responden correctamente con JWT válido e inválido
  - Asegurarse de que todos los tests pasen antes de continuar con el frontend

- [x] 10. Frontend — Componente `NotificationBadge`
  - [x] 10.1 Crear `frontend/src/components/NotificationBadge.jsx` (o `.tsx`)
    - Hook interno con `setInterval` de 30 segundos que llama a `GET /notificaciones/no-leidas`
    - Mostrar badge numérico sobre ícono de notificaciones cuando `total > 0`
    - Ocultar badge cuando `total === 0`
    - Limpiar el intervalo en `useEffect` cleanup para evitar memory leaks
    - Actualizar badge inmediatamente tras marcar una notificación como leída (sin recargar página)
    - _Requisitos: 6.1, 6.2, 6.3, 6.4_

  - [x] 10.2 Escribir test de propiedad: badge refleja conteo correcto
    - **Propiedad 15: Badge refleja conteo correcto**
    - **Valida: Requisitos 6.1, 6.2**
    - Verificar con `@given(st.integers(min_value=0))` que badge se muestra cuando N > 0 y se oculta cuando N = 0

- [x] 11. Frontend — Componente `NotificationBanner`
  - [x] 11.1 Crear `frontend/src/components/NotificationBanner.jsx` (o `.tsx`)
    - Renderizar solo cuando el usuario tiene rol `ADMIN` y existe al menos una notificación `RENOVACION_PLAN` no leída
    - No renderizar para usuarios con rol `MECANICO`
    - Banner no bloqueante en la parte superior de la pantalla con el mensaje de vencimiento
    - Botón de cierre que llama a `PATCH /notificaciones/{id}/leer` y oculta el banner sin recargar página
    - _Requisitos: 8.1, 8.2, 8.3, 8.4_

  - [x] 11.2 Escribir test de propiedad: banner visible solo para ADMIN
    - **Propiedad 14: Banner de renovación visible solo para ADMIN**
    - **Valida: Requisitos 8.1, 8.3, 8.4**
    - Verificar que con notificaciones `RENOVACION_PLAN` no leídas, el banner se renderiza para ADMIN y no se renderiza para MECANICO

- [x] 12. Integración final y cableado
  - [x] 12.1 Verificar integración completa del flujo de asignación
    - Confirmar que `crear_ticket` y `actualizar_ticket` en `TicketService` invocan `asignar_mecanico` correctamente
    - Verificar atomicidad: si la notificación falla, el ticket no se persiste
    - _Requisitos: 3.1, 3.2, 3.3_

  - [x] 12.2 Integrar `NotificationBadge` en la barra de navegación del frontend
    - Agregar `<NotificationBadge />` al componente de navbar existente
    - Verificar que el polling se inicia al montar y se detiene al desmontar
    - _Requisitos: 6.1, 6.4_

  - [x] 12.3 Integrar `NotificationBanner` en el layout principal del frontend
    - Agregar `<NotificationBanner />` al layout raíz, visible solo para ADMIN
    - _Requisitos: 8.1, 8.3_

  - [x] 12.4 Escribir tests de integración end-to-end
    - Flujo completo: crear ticket con mecánico → verificar notificación `TICKET_ASIGNADO` en BD
    - Flujo completo: ejecutar verificador → verificar notificaciones `RENOVACION_PLAN` en BD
    - Test: endpoint `GET /notificaciones/no-leidas` responde en < 300ms con índice compuesto activo
    - _Requisitos: 4.4_

- [x] 13. Checkpoint final — Todos los tests deben pasar
  - Ejecutar suite completa: propiedades Hypothesis (15 propiedades), tests de ejemplo y tests de integración
  - Verificar cobertura de todos los endpoints con JWT válido, inválido y cross-tenant
  - Asegurarse de que todos los tests pasen antes de dar por completada la implementación

## Notas

- Las tareas marcadas con `*` son opcionales y pueden omitirse para un MVP más rápido
- Cada tarea referencia requisitos específicos para trazabilidad
- Los checkpoints garantizan validación incremental antes de avanzar a la siguiente capa
- Los tests de propiedades usan Hypothesis con `@settings(max_examples=100)` mínimo
- El `taller_id` se obtiene **siempre** del JWT, nunca del body ni query params (invariante multi-tenant)
- La atomicidad ticket + notificación se garantiza con `db.begin_nested()` (savepoint)
- El SUPER_ADMIN (taller_id=null) no puede acceder a ningún endpoint de notificaciones
