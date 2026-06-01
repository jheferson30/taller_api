# Documento de Requisitos: Planes y Facturación

## Introducción

Este documento describe los requisitos para el sistema de planes, límites y facturación del SaaS de gestión de talleres mecánicos.

El sistema maneja tres planes (Básico, Pro, Enterprise) con límites configurables por plan. La facturación es **manual** — el SUPER_ADMIN registra los pagos. El sistema notifica al ADMIN del taller sobre vencimientos y límites, pero **no bloquea operaciones** cuando se superan los límites. La suspensión automática por vencimiento sí bloquea el acceso.

---

## Glosario

- **Plan**: Nivel de suscripción del taller. Define los límites de uso del sistema.
- **Básico**: Plan de entrada con límites reducidos.
- **Pro**: Plan intermedio con límites ampliados.
- **Enterprise**: Plan sin límites o con límites muy altos.
- **Límite_Plan**: Restricción de uso definida por el plan: máximo de usuarios, tickets por mes, almacenamiento.
- **Facturación_Manual**: El SUPER_ADMIN registra manualmente el pago recibido de un taller.
- **Fecha_Vencimiento**: Fecha hasta la cual el pago del taller está vigente.
- **Notificacion_Limite**: Alerta interna enviada al ADMIN del taller cuando se acerca o supera un límite del plan.
- **Suspension_Automatica**: Cambio automático del estado del taller a `SUSPENDIDO` cuando vence el pago.

---

## Requisitos

### Requisito 1: Definición de Planes

**User Story:** Como SUPER_ADMIN, quiero definir planes con límites específicos, para ofrecer diferentes niveles de servicio a mis clientes.

#### Criterios de Aceptación

1. THE Sistema SHALL crear la tabla `planes` con los campos: `id` (PK), `nombre` (enum: `BASICO`, `PRO`, `ENTERPRISE`), `max_usuarios` (integer, nullable — null = sin límite), `max_tickets_mes` (integer, nullable), `max_almacenamiento_mb` (integer, nullable), `precio_mensual` (integer, en centavos de la moneda base), `activo` (boolean, default true).
2. THE Sistema SHALL insertar los tres planes por defecto al inicializar la base de datos: `BASICO`, `PRO`, `ENTERPRISE`.
3. THE Sistema SHALL exponer `GET /admin/planes` protegido con `@require_role("SUPER_ADMIN")` para listar todos los planes con sus límites.
4. THE Sistema SHALL exponer `PATCH /admin/planes/{plan_id}` protegido con `@require_role("SUPER_ADMIN")` para actualizar los límites de un plan.
5. WHEN el SUPER_ADMIN actualiza los límites de un plan, THE Sistema SHALL aplicar los nuevos límites a todos los talleres con ese plan a partir del siguiente ciclo de facturación.
6. IF se intenta eliminar un plan que tiene talleres activos asignados, THEN THE Sistema SHALL retornar HTTP 400 con el mensaje "No se puede eliminar un plan con talleres activos".

---

### Requisito 2: Asignación de Plan a Taller

**User Story:** Como SUPER_ADMIN, quiero asignar un plan a cada taller, para controlar los límites de uso de cada cliente.

#### Criterios de Aceptación

1. THE Sistema SHALL extender la tabla `talleres` con: `plan_id` (FK → `planes.id`, nullable), `fecha_vencimiento` (timestamp, nullable), `fecha_ultimo_pago` (timestamp, nullable), `monto_ultimo_pago` (integer, nullable).
2. WHEN se crea un nuevo Taller, THE Sistema SHALL asignar `plan_id = null` (sin plan) hasta que el SUPER_ADMIN asigne uno explícitamente.
3. THE Sistema SHALL exponer `PATCH /talleres/{taller_id}/plan` protegido con `@require_role("SUPER_ADMIN")` para asignar o cambiar el plan de un taller.
4. WHEN el SUPER_ADMIN asigna un plan a un Taller, THE Sistema SHALL registrar la acción en Audit_Log con acción `PLAN_ASIGNADO` incluyendo el plan anterior y el nuevo en `details`.
5. THE Sistema SHALL incluir `plan_id`, `nombre_plan`, `fecha_vencimiento` y `dias_para_vencer` en la respuesta de `GET /talleres/{taller_id}`.
6. THE Sistema SHALL calcular `dias_para_vencer` como la diferencia entre `fecha_vencimiento` y la fecha actual, retornando `null` si no hay fecha de vencimiento.

---

### Requisito 3: Registro Manual de Pagos

**User Story:** Como SUPER_ADMIN, quiero registrar manualmente los pagos recibidos de cada taller, para mantener el estado de facturación actualizado.

#### Criterios de Aceptación

1. THE Sistema SHALL crear la tabla `pagos_taller` con los campos: `id` (PK), `taller_id` (FK → `talleres.id`), `monto` (integer, en centavos), `fecha_pago` (timestamp), `periodo_desde` (date), `periodo_hasta` (date), `metodo_pago` (string, nullable), `referencia` (string, nullable), `registrado_por` (FK → `users.id`), `notas` (text, nullable), `fecha_creacion` (timestamp).
2. THE Sistema SHALL exponer `POST /talleres/{taller_id}/pagos` protegido con `@require_role("SUPER_ADMIN")` para registrar un pago.
3. WHEN el SUPER_ADMIN registra un pago, THE Sistema SHALL actualizar `fecha_vencimiento` del taller al valor de `periodo_hasta` del pago, actualizar `fecha_ultimo_pago` y `monto_ultimo_pago`, y si el taller estaba `SUSPENDIDO` por vencimiento, cambiar su estado a `ACTIVO` automáticamente.
4. THE Sistema SHALL exponer `GET /talleres/{taller_id}/pagos` protegido con `@require_role("SUPER_ADMIN")` para listar el historial de pagos de un taller con paginación.
5. THE Sistema SHALL registrar cada pago en Audit_Log con acción `PAGO_REGISTRADO` incluyendo el monto y período en `details`.
6. IF se registra un pago para un Taller con `estado = CANCELADO`, THEN THE Sistema SHALL retornar HTTP 400 con el mensaje "No se pueden registrar pagos para un taller cancelado".

---

### Requisito 4: Suspensión Automática por Vencimiento

**User Story:** Como SUPER_ADMIN, quiero que el sistema suspenda automáticamente los talleres con pago vencido, para no tener que hacerlo manualmente.

#### Criterios de Aceptación

1. THE Sistema SHALL ejecutar una tarea programada diaria (Celery beat) que verifique todos los talleres con `estado = ACTIVO` y `fecha_vencimiento < NOW()`.
2. WHEN la tarea programada detecta un Taller con pago vencido, THE Sistema SHALL cambiar su `estado` a `SUSPENDIDO`, registrar `fecha_suspension = NOW()` y registrar la acción en Audit_Log con acción `TALLER_SUSPEND` y `details = {"motivo": "vencimiento_automatico"}`.
3. THE Sistema SHALL enviar una notificación interna al ADMIN del taller cuando su taller sea suspendido automáticamente, indicando la fecha de vencimiento y cómo contactar al SUPER_ADMIN.
4. THE Sistema SHALL ejecutar la tarea de verificación de vencimientos una vez al día a las 00:00 en la zona horaria del servidor.
5. IF un Taller tiene `plan_id = null` (sin plan asignado), THEN THE Sistema SHALL omitir la verificación de vencimiento para ese taller.

---

### Requisito 5: Notificaciones de Límites del Plan

**User Story:** Como ADMIN del taller, quiero recibir notificaciones cuando me acerco o supero los límites de mi plan, para tomar decisiones antes de que afecte la operación.

#### Criterios de Aceptación

1. THE Sistema SHALL verificar el consumo de recursos del taller en cada operación de creación de ticket y de usuario.
2. WHEN un Taller alcanza el 80% del límite de tickets mensuales de su plan, THE Sistema SHALL enviar una notificación interna al ADMIN del taller con el mensaje "Has usado el 80% de tus tickets mensuales. Considera actualizar tu plan.".
3. WHEN un Taller supera el 100% del límite de tickets mensuales de su plan, THE Sistema SHALL enviar una notificación interna al ADMIN del taller con el mensaje "Has superado el límite de tickets de tu plan. Contacta al administrador para actualizar.".
4. WHEN un Taller alcanza el 80% del límite de usuarios de su plan, THE Sistema SHALL enviar una notificación interna al ADMIN del taller.
5. WHEN un Taller supera el 100% del límite de usuarios de su plan, THE Sistema SHALL enviar una notificación interna al ADMIN del taller.
6. THE Sistema SHALL NO bloquear ninguna operación cuando se supera un límite del plan — solo notificar al ADMIN.
7. THE Sistema SHALL enviar cada notificación de límite una sola vez por ciclo mensual, no en cada operación que supere el límite.
8. IF el plan del taller tiene `max_tickets_mes = null` o `max_usuarios = null`, THEN THE Sistema SHALL omitir la verificación de ese límite (sin límite configurado).

---

### Requisito 6: Notificaciones de Vencimiento Próximo

**User Story:** Como ADMIN del taller, quiero recibir notificaciones antes de que venza mi suscripción, para renovar a tiempo y evitar interrupciones.

#### Criterios de Aceptación

1. THE Sistema SHALL verificar diariamente los talleres con `fecha_vencimiento` próxima como parte de la tarea programada del Requisito 4.
2. WHEN un Taller tiene `fecha_vencimiento` a 7 días o menos, THE Sistema SHALL enviar una notificación interna al ADMIN del taller indicando la fecha de vencimiento y cómo renovar.
3. WHEN un Taller tiene `fecha_vencimiento` a 3 días o menos, THE Sistema SHALL enviar una segunda notificación interna al ADMIN del taller con urgencia mayor.
4. WHEN un Taller tiene `fecha_vencimiento` a 1 día o menos, THE Sistema SHALL enviar una tercera notificación interna al ADMIN del taller.
5. THE Sistema SHALL enviar cada notificación de vencimiento una sola vez (a los 7 días, a los 3 días, al día siguiente), no repetirla diariamente.
