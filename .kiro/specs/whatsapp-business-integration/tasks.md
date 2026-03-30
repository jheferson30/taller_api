# Plan de Implementación: Integración WhatsApp Business

## Overview

Implementación incremental de la integración con WhatsApp Business API (Twilio como proveedor inicial). Cada tarea es atómica y enfocada en un único archivo o responsabilidad.

## Tasks

- [x] 1. Migración de base de datos: extender ConfiguracionTaller
  - Crear archivo `db/migracion_whatsapp_2026.sql` con el `ALTER TABLE` para agregar `whatsapp_token`, `whatsapp_phone_id`, `whatsapp_enabled`
  - _Requirements: 1.1_

- [x] 2. Migración de base de datos: crear tabla log_notificacion
  - Agregar al mismo archivo SQL el `CREATE TABLE log_notificacion` con sus índices
  - _Requirements: 7.1_

- [x] 3. Actualizar modelo SQLAlchemy: ConfiguracionTaller
  - Agregar los tres campos WhatsApp al modelo en `app/modelos/configuracion_taller.py`
  - _Requirements: 1.1_

- [x] 4. Crear modelo SQLAlchemy: LogNotificacion
  - Crear `app/modelos/log_notificacion.py` con el modelo completo
  - _Requirements: 7.1_

- [x] 5. Crear enums y clase base: WhatsAppService
  - Crear `app/servicios/whatsapp_service.py` con `TipoEvento`, `ResultadoEnvio` y la clase abstracta `WhatsAppService`
  - _Requirements: 1.3, 2.1, 3.1, 4.1_

- [x] 6. Implementar TwilioWhatsAppService — lógica de omisión y validación
  - Crear `app/servicios/twilio_whatsapp_service.py`
  - Implementar los casos de omisión: `whatsapp_enabled=false`, token vacío, teléfono ausente
  - Persistir log en cada caso
  - _Requirements: 1.3, 1.4, 2.3, 7.4_

- [x] 7. Implementar TwilioWhatsAppService — construcción de mensajes
  - Agregar método privado `_construir_mensaje(tipo, ticket, vehiculo)` en `twilio_whatsapp_service.py`
  - Cubrir los tres tipos: RECEPCION, FINALIZACION, ENTREGA
  - _Requirements: 2.2, 3.2, 3.3, 4.2, 4.3_

- [x] 8. Implementar TwilioWhatsAppService — llamada HTTP a Twilio
  - Agregar la llamada real con `httpx` en `enviar_notificacion`
  - Manejar errores HTTP y timeout, persistir resultado en log
  - _Requirements: 2.4, 3.4, 4.4_

- [x] 9. Implementar TwilioWhatsAppService — envío manual
  - Implementar `enviar_mensaje_manual` en `twilio_whatsapp_service.py`
  - Validar longitud del mensaje (1–1024 chars) y persistir log
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 6.3, 6.4_

- [x] 10. Crear esquemas Pydantic: WhatsApp
  - Crear `app/esquemas/whatsapp_schema.py` con `WhatsAppConfigUpdate`, `MensajeManualRequest`, `LogNotificacionResponse`
  - _Requirements: 1.2, 5.2, 6.3, 7.2_

- [x] 11. Crear router: whatsapp_ruta — webhook GET (verificación Meta)
  - Crear `app/rutas/whatsapp_ruta.py` con el endpoint `GET /whatsapp/webhook`
  - Leer `WHATSAPP_VERIFY_TOKEN` de env y responder al challenge
  - _Requirements: 8.1, 8.4_

- [x] 12. Agregar endpoint webhook POST en whatsapp_ruta
  - Agregar `POST /whatsapp/webhook` en `app/rutas/whatsapp_ruta.py`
  - Registrar mensajes entrantes en log con tipo `ENTRANTE`, retornar HTTP 200 siempre
  - _Requirements: 8.2, 8.3, 8.5_

- [x] 13. Agregar endpoint GET logs en whatsapp_ruta
  - Agregar `GET /api/mobile/whatsapp/logs` con filtro opcional `?ticket_id=` y límite 100
  - _Requirements: 7.2, 7.3_

- [x] 14. Agregar endpoint POST envío manual móvil en whatsapp_ruta
  - Agregar `POST /api/mobile/tickets/{ticket_id}/whatsapp` en `app/rutas/whatsapp_ruta.py`
  - Retornar `{"ok": true/false, ...}` con HTTP 200 siempre
  - _Requirements: 6.1, 6.2, 6.4, 6.5_

- [x] 15. Agregar endpoint POST envío manual web en whatsapp_ruta
  - Agregar `POST /api/whatsapp/tickets/{ticket_id}/mensaje` en `app/rutas/whatsapp_ruta.py`
  - _Requirements: 5.1, 5.3, 5.4_

- [x] 16. Actualizar configuracion_ruta: campos WhatsApp
  - Agregar lectura y escritura de `whatsapp_token`, `whatsapp_phone_id`, `whatsapp_enabled` en `app/rutas/configuracion_ruta.py`
  - Validar que `whatsapp_phone_id` sea numérico antes de persistir (HTTP 422 si no)
  - _Requirements: 1.1, 1.2_

- [x] 17. Registrar whatsapp_ruta y modelo en main.py
  - Importar `log_notificacion` en `app/main.py` para que `Base.metadata.create_all` lo incluya
  - Registrar `whatsapp_ruta.router` en la app
  - _Requirements: 8.1, 8.2_

- [x] 18. Integrar notificación RECEPCION en ticket_ruta
  - En `app/rutas/ticket_ruta.py`, después del `db.commit()` de creación de ticket, disparar `asyncio.create_task(whatsapp_service.enviar_notificacion(RECEPCION, ...))`
  - _Requirements: 2.1_

- [x] 19. Integrar notificación FINALIZACION en ticket_service
  - En `app/servicios/ticket_service.py`, al final de `finalizar_ticket()`, disparar la notificación FINALIZACION como fire-and-forget
  - _Requirements: 3.1_

- [x] 20. Integrar notificación ENTREGA en mobile_api_ruta
  - En `app/rutas/mobile_api_ruta.py`, en `entregar_ticket_mobile()`, disparar la notificación ENTREGA como fire-and-forget
  - _Requirements: 4.1_

- [x] 21. Integrar notificación ENTREGA en ticket_ruta (endpoint web)
  - En `app/rutas/ticket_ruta.py`, en `marcar_entregado()`, disparar la notificación ENTREGA como fire-and-forget
  - _Requirements: 4.1_

- [x] 22. Checkpoint — verificar integración básica
  - Asegurar que todos los tests existentes siguen pasando, preguntar al usuario si hay dudas antes de continuar con los tests de la nueva feature.

- [x] 23. Crear archivo de tests: test_whatsapp_service.py — unit tests
  - Crear `tests/test_whatsapp_service.py`
  - [x] 23.1 Test: servicio deshabilitado retorna OMITIDO sin llamada HTTP
    - _Requirements: 1.3_
  - [x] 23.2 Test: token vacío retorna ERROR sin llamada HTTP
    - _Requirements: 1.4_
  - [x] 23.3 Test: teléfono ausente retorna OMITIDO con motivo "sin_telefono"
    - _Requirements: 2.3_
  - [ ]* 23.4 Property test — Property 3: servicio deshabilitado produce OMITIDO
    - **Property 3: Servicio deshabilitado produce resultado OMITIDO**
    - **Validates: Requirements 1.3, 7.4**
  - [ ]* 23.5 Property test — Property 4: token vacío no llama HTTP
    - **Property 4: Token vacío produce log de error sin llamada HTTP**
    - **Validates: Requirements 1.4**
  - [ ]* 23.6 Property test — Property 7: teléfono ausente produce OMITIDO
    - **Property 7: Teléfono ausente produce log OMITIDO con motivo "sin_telefono"**
    - **Validates: Requirements 2.3**

- [x] 24. Crear archivo de tests: test_whatsapp_service.py — mensajes y log
  - [x] 24.1 Test: mensaje RECEPCION contiene nombre, placa, código, motivo
    - _Requirements: 2.2_
  - [x] 24.2 Test: mensaje FINALIZACION contiene total y saldo
    - _Requirements: 3.2_
  - [x] 24.3 Test: mensaje ENTREGA omite recomendaciones si están vacías
    - _Requirements: 4.3_
  - [x] 24.4 Test: log persiste tipo_evento, resultado y created_at no nulos
    - _Requirements: 7.1_
  - [ ]* 24.5 Property test — Property 6: mensaje contiene campos requeridos según tipo
    - **Property 6: Mensaje de notificación contiene los campos requeridos según tipo de evento**
    - **Validates: Requirements 2.2, 3.2, 4.2**
  - [ ]* 24.6 Property test — Property 11: log persiste todos los campos requeridos
    - **Property 11: Log persiste todos los campos requeridos**
    - **Validates: Requirements 5.5, 7.1**

- [x] 25. Crear archivo de tests: test_whatsapp_ruta.py — webhook y logs
  - Crear `tests/test_whatsapp_ruta.py`
  - [x] 25.1 Test: GET /whatsapp/webhook responde al challenge correctamente
    - _Requirements: 8.1_
  - [x] 25.2 Test: GET /whatsapp/webhook con token incorrecto retorna 403
    - _Requirements: 8.4_
  - [x] 25.3 Test: POST /whatsapp/webhook con mensaje entrante crea log ENTRANTE
    - _Requirements: 8.3_
  - [x] 25.4 Test: GET /api/mobile/whatsapp/logs retorna estructura correcta
    - _Requirements: 7.2_
  - [ ]* 25.5 Property test — Property 12: logs retorna máximo 100 ordenados por fecha desc
    - **Property 12: Endpoint de logs retorna máximo 100 registros ordenados por fecha descendente**
    - **Validates: Requirements 7.2**
  - [ ]* 25.6 Property test — Property 13: filtro ticket_id es correcto
    - **Property 13: Filtro por ticket_id en logs es correcto**
    - **Validates: Requirements 7.3**
  - [ ]* 25.7 Property test — Property 14: webhook registra mensajes entrantes con tipo ENTRANTE
    - **Property 14: Webhook registra mensajes entrantes con tipo ENTRANTE**
    - **Validates: Requirements 8.3, 8.5**

- [x] 26. Crear archivo de tests: test_whatsapp_configuracion.py
  - Crear `tests/test_whatsapp_configuracion.py`
  - [x] 26.1 Test: envío manual con mensaje vacío retorna HTTP 422
    - _Requirements: 5.2, 6.3_
  - [x] 26.2 Test: envío manual con mensaje >1024 chars retorna HTTP 422
    - _Requirements: 5.2, 6.3_
  - [x] 26.3 Test: envío manual exitoso retorna message_id
    - _Requirements: 5.3, 6.4_
  - [ ]* 26.4 Property test — Property 1: credenciales persisten y se recuperan correctamente
    - **Property 1: Credenciales persisten y se recuperan correctamente**
    - **Validates: Requirements 1.1**
  - [ ]* 26.5 Property test — Property 2: phone_id rechaza no-numéricos
    - **Property 2: Validación de phone_id rechaza no-numéricos**
    - **Validates: Requirements 1.2**
  - [ ]* 26.6 Property test — Property 9: validación de longitud de mensaje manual
    - **Property 9: Validación de longitud de mensaje manual**
    - **Validates: Requirements 5.2, 6.3**
  - [ ]* 26.7 Property test — Property 10: envío manual exitoso retorna message_id
    - **Property 10: Envío manual exitoso retorna message_id**
    - **Validates: Requirements 5.3, 6.4**

- [x] 27. Checkpoint final — todos los tests pasan
  - Ejecutar `pytest tests/test_whatsapp_service.py tests/test_whatsapp_ruta.py tests/test_whatsapp_configuracion.py --run`
  - Asegurar que los tests existentes no se rompieron, preguntar al usuario si hay dudas.

## Notes

- Tareas marcadas con `*` son opcionales y pueden omitirse para un MVP más rápido
- Cada tarea toca un único archivo o responsabilidad para evitar bloqueos
- Las notificaciones son fire-and-forget con `asyncio.create_task()` — nunca bloquean el flujo del ticket
- El proveedor Twilio puede reemplazarse por Meta Cloud API cambiando solo `twilio_whatsapp_service.py`
- Hypothesis ya está instalado en el proyecto (ver `.hypothesis/`)
