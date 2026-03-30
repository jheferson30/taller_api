# Documento de Requerimientos

## Introducción

Integración de WhatsApp Business API en el sistema de taller mecánico para automatizar la comunicación con los clientes. El sistema enviará notificaciones automáticas en los momentos clave del ciclo de vida de un ticket (recepción, avance, finalización y entrega), y permitirá al taller enviar mensajes manuales desde el frontend web y la app móvil.

## Glosario

- **WhatsApp_Service**: Módulo del backend responsable de enviar mensajes a través de la WhatsApp Business API.
- **Notificacion_WhatsApp**: Mensaje enviado al número de teléfono del propietario del vehículo a través de WhatsApp Business.
- **Plantilla_Mensaje**: Mensaje pre-aprobado por Meta (WhatsApp Business) con variables dinámicas (nombre, placa, código de ticket, etc.).
- **Webhook_WhatsApp**: Endpoint HTTP del backend que recibe eventos entrantes desde la plataforma de WhatsApp Business (confirmaciones de entrega, respuestas de clientes).
- **Ticket**: Orden de servicio del taller que representa el trabajo realizado sobre un vehículo.
- **Propietario**: Persona dueña del vehículo registrada en el sistema con nombre y número de teléfono.
- **Configuracion_Taller**: Registro en base de datos que almacena parámetros globales del taller, incluyendo credenciales de WhatsApp Business.
- **Log_Notificacion**: Registro persistente de cada intento de envío de mensaje con su resultado (éxito o error).

---

## Requerimientos

### Requerimiento 1: Configuración de Credenciales de WhatsApp Business

**User Story:** Como administrador del taller, quiero configurar las credenciales de WhatsApp Business desde el panel de configuración, para que el sistema pueda enviar mensajes sin necesidad de modificar código.

#### Criterios de Aceptación

1. THE Configuracion_Taller SHALL almacenar los siguientes campos para WhatsApp Business: `whatsapp_token` (token de acceso), `whatsapp_phone_id` (ID del número de teléfono), `whatsapp_enabled` (habilitado/deshabilitado).
2. WHEN el administrador guarda la configuración de WhatsApp, THE Sistema SHALL validar que `whatsapp_phone_id` tenga formato numérico antes de persistir.
3. IF `whatsapp_enabled` es `false`, THEN THE WhatsApp_Service SHALL omitir el envío de cualquier notificación sin retornar error.
4. WHERE `whatsapp_token` está vacío o nulo, THE WhatsApp_Service SHALL registrar un error de configuración en el Log_Notificacion y no intentar el envío.

---

### Requerimiento 2: Notificación Automática al Recibir el Vehículo

**User Story:** Como propietario del vehículo, quiero recibir un mensaje de WhatsApp cuando mi vehículo ingresa al taller, para tener confirmación de que fue recibido correctamente.

#### Criterios de Aceptación

1. WHEN un Ticket es creado con estado `ABIERTO`, THE WhatsApp_Service SHALL enviar una Notificacion_WhatsApp al número `telefono_propietario` del vehículo asociado.
2. THE Notificacion_WhatsApp de recepción SHALL incluir: nombre del propietario, placa del vehículo, código del ticket y motivo de visita.
3. IF `telefono_propietario` está vacío o nulo en el momento de crear el ticket, THEN THE WhatsApp_Service SHALL omitir el envío y registrar el evento en el Log_Notificacion con motivo "sin_telefono".
4. IF la llamada a la WhatsApp Business API retorna un código de error HTTP, THEN THE WhatsApp_Service SHALL registrar el error en el Log_Notificacion y SHALL continuar el flujo normal de creación del ticket sin interrumpirlo.

---

### Requerimiento 3: Notificación Automática al Finalizar el Servicio

**User Story:** Como propietario del vehículo, quiero recibir un mensaje de WhatsApp cuando el servicio de mi vehículo esté listo, para saber cuándo puedo pasar a recogerlo.

#### Criterios de Aceptación

1. WHEN un Ticket cambia de estado a `FINALIZADO`, THE WhatsApp_Service SHALL enviar una Notificacion_WhatsApp al número `telefono_propietario` del vehículo asociado.
2. THE Notificacion_WhatsApp de finalización SHALL incluir: nombre del propietario, placa del vehículo, código del ticket, total del servicio y saldo pendiente.
3. IF `saldo_pendiente` es 0, THEN THE Notificacion_WhatsApp SHALL indicar que el servicio está completamente pagado.
4. IF la llamada a la WhatsApp Business API retorna un código de error HTTP, THEN THE WhatsApp_Service SHALL registrar el error en el Log_Notificacion y SHALL continuar el flujo normal de finalización del ticket sin interrumpirlo.

---

### Requerimiento 4: Notificación Automática al Entregar el Vehículo

**User Story:** Como administrador del taller, quiero que el sistema envíe un mensaje de confirmación de entrega al cliente, para cerrar el ciclo de comunicación del servicio.

#### Criterios de Aceptación

1. WHEN un Ticket cambia de estado a `ENTREGADO`, THE WhatsApp_Service SHALL enviar una Notificacion_WhatsApp al número `telefono_propietario` del vehículo asociado.
2. THE Notificacion_WhatsApp de entrega SHALL incluir: nombre del propietario, placa del vehículo, código del ticket y recomendaciones (si existen).
3. IF `recomendaciones` está vacío o nulo, THEN THE Notificacion_WhatsApp SHALL omitir la sección de recomendaciones del mensaje.
4. IF la llamada a la WhatsApp Business API retorna un código de error HTTP, THEN THE WhatsApp_Service SHALL registrar el error en el Log_Notificacion y SHALL continuar el flujo normal de entrega del ticket sin interrumpirlo.

---

### Requerimiento 5: Envío Manual de Mensaje desde el Frontend Web

**User Story:** Como operador del taller, quiero poder enviar un mensaje de WhatsApp manualmente a un cliente desde la vista del ticket, para comunicarme con él en cualquier momento del proceso.

#### Criterios de Aceptación

1. WHEN el operador envía un mensaje manual desde la vista del ticket, THE WhatsApp_Service SHALL enviar el texto libre al número `telefono_propietario` del vehículo asociado al ticket.
2. THE Sistema SHALL validar que el texto del mensaje manual tenga entre 1 y 1024 caracteres antes de enviarlo.
3. IF el envío manual es exitoso, THEN THE Sistema SHALL retornar confirmación con el identificador del mensaje devuelto por la API de WhatsApp.
4. IF el envío manual falla, THEN THE Sistema SHALL retornar un mensaje de error descriptivo al operador sin interrumpir otras operaciones del ticket.
5. THE Log_Notificacion SHALL registrar cada envío manual con: ticket_id, número destino, texto enviado, resultado y timestamp.

---

### Requerimiento 6: Envío Manual de Mensaje desde la App Móvil

**User Story:** Como mecánico, quiero poder enviar un mensaje de WhatsApp al cliente desde la app móvil, para informarle sobre el avance del trabajo sin necesidad de acceder al frontend web.

#### Criterios de Aceptación

1. WHEN el mecánico envía un mensaje manual desde la app móvil, THE WhatsApp_Service SHALL enviar el texto al número `telefono_propietario` del vehículo asociado al ticket.
2. THE Sistema SHALL exponer un endpoint `POST /api/mobile/tickets/{ticket_id}/whatsapp` que acepte el campo `mensaje` (texto libre).
3. THE Sistema SHALL validar que `mensaje` tenga entre 1 y 1024 caracteres antes de enviarlo.
4. IF el envío es exitoso, THEN THE Sistema SHALL retornar `{"ok": true, "message_id": "<id>"}`.
5. IF el envío falla, THEN THE Sistema SHALL retornar `{"ok": false, "error": "<descripción>"}` con código HTTP 200 para no interrumpir el flujo de la app.

---

### Requerimiento 7: Registro y Consulta de Log de Notificaciones

**User Story:** Como administrador del taller, quiero consultar el historial de mensajes enviados por WhatsApp, para auditar la comunicación con los clientes y detectar fallos.

#### Criterios de Aceptación

1. THE Log_Notificacion SHALL persistir los siguientes campos por cada intento de envío: `id`, `ticket_id` (nullable), `telefono_destino`, `tipo_evento` (RECEPCION, FINALIZACION, ENTREGA, MANUAL), `mensaje_enviado`, `resultado` (ENVIADO, ERROR, OMITIDO), `error_detalle` (nullable), `created_at`.
2. THE Sistema SHALL exponer un endpoint `GET /api/mobile/whatsapp/logs` que retorne los últimos 100 registros del Log_Notificacion ordenados por `created_at` descendente.
3. WHEN se consulta el log con el parámetro `ticket_id`, THE Sistema SHALL filtrar los registros por ese ticket.
4. IF `whatsapp_enabled` es `false`, THEN THE Log_Notificacion SHALL registrar el evento con resultado `OMITIDO` para mantener trazabilidad.

---

### Requerimiento 8: Webhook para Recibir Eventos de WhatsApp

**User Story:** Como administrador del taller, quiero que el sistema reciba confirmaciones de entrega y respuestas de los clientes desde WhatsApp, para tener visibilidad del estado real de los mensajes enviados.

#### Criterios de Aceptación

1. THE Sistema SHALL exponer un endpoint `GET /whatsapp/webhook` que responda al desafío de verificación de Meta con el token configurado en `WHATSAPP_VERIFY_TOKEN`.
2. THE Sistema SHALL exponer un endpoint `POST /whatsapp/webhook` que reciba y procese los eventos entrantes de la WhatsApp Business API.
3. WHEN se recibe un evento de tipo `message` en el webhook, THE Sistema SHALL registrar el mensaje entrante en el Log_Notificacion con tipo_evento `ENTRANTE`.
4. IF el token de verificación del webhook no coincide con `WHATSAPP_VERIFY_TOKEN`, THEN THE Sistema SHALL retornar HTTP 403.
5. THE Sistema SHALL retornar HTTP 200 ante cualquier evento de webhook válido para evitar reintentos de Meta.

