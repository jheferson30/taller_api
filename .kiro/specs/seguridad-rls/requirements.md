# Requirements Document: Seguridad RLS — Hallazgos de Auditoría

## Introduction

Este documento define los requisitos para resolver los hallazgos críticos, altos y medios de
Row-Level Security (RLS) identificados en la auditoría de seguridad del sistema SaaS multi-tenant
de gestión de talleres mecánicos.

**Contexto del Sistema:**
- Backend: FastAPI + PostgreSQL
- Autenticación: JWT con access/refresh tokens
- Infraestructura existente: `TenantRepository` base con filtrado por `taller_id`, decoradores
  `@require_auth` y `@require_role`
- Invariante de seguridad: el `taller_id` del usuario SIEMPRE proviene de `request.state.taller_id`
  (extraído del JWT) — nunca del body, query params ni headers del cliente

**Hallazgos pendientes de la auditoría:**

| ID   | Severidad | Archivo                     | Descripción                                                   |
|------|-----------|-----------------------------|---------------------------------------------------------------|
| C-03 | Crítico   | whatsapp_ruta.py L70,88     | Endpoints de envío WhatsApp sin autenticación                 |
| C-04 | Crítico   | whatsapp_ruta.py L109       | GET logs WhatsApp sin auth ni filtro taller_id                |
| C-05 | Crítico   | whatsapp_ruta.py L~47       | Webhook routing incorrecto para multi-taller                  |
| C-06 | Crítico   | economia_ruta.py L20-80     | Helpers de queries sin filtro taller_id                       |
| C-07 | Crítico   | whatsapp_ruta.py L~80,100   | ticket.taller_id usado sin verificar contra JWT               |
| C-09 | Crítico   | pdf_ruta.py L~43            | TicketRepository instanciado sin taller_id                    |
| A-01 | Alto      | upload_ruta.py L32,61,89    | Endpoints de upload sin @require_auth explícito               |
| A-02 | Alto      | upload_ruta.py L117,127,137 | Archivos servidos sin autenticación                           |
| A-03 | Alto      | pdf_ruta.py L20,~61,~109    | Endpoints de PDF sin autenticación                            |
| M-01 | Medio     | seguridad_ruta.py L161      | cambiar_password_admin sin @require_auth                      |
| M-02 | Medio     | ticket_ruta.py              | Múltiples endpoints sin @require_auth explícito               |
| M-03 | Medio     | configuracion_ruta.py L~54  | listar_mecanicos sin @require_auth                            |

**Archivos que se modificarán:**
- `app/rutas/whatsapp_ruta.py` (C-03, C-04, C-05, C-07)
- `app/rutas/economia_ruta.py` (C-06)
- `app/rutas/pdf_ruta.py` (C-09, A-03)
- `app/rutas/upload_ruta.py` (A-01, A-02)
- `app/rutas/seguridad_ruta.py` (M-01)
- `app/rutas/ticket_ruta.py` (M-02)
- `app/rutas/configuracion_ruta.py` (M-03)
- `scripts/rls_audit.py` (nuevo)
- `tests/test_rls_audit.py` (nuevo)
- `tests/test_rls_properties.py` (nuevo)

## Glossary

- **RLS_Guard**: Mecanismo de Row-Level Security que garantiza aislamiento de datos entre tenants,
  filtrando toda query por `taller_id` extraído del JWT. Nunca acepta `taller_id` del body,
  query params ni headers del cliente.
- **Tenant_Repository**: Repositorio base que implementa filtrado automático por `taller_id`.
  Todo repositorio de datos operativos hereda de esta clase.
- **Webhook_Router**: Componente que determina a qué taller pertenece un mensaje entrante de
  Twilio usando el campo `To` del payload para buscar el taller por número de teléfono registrado.
- **Cross_Tenant_Access**: Intento de acceder a datos de un taller diferente al del usuario
  autenticado. Debe retornar HTTP 404 — nunca 403 — para no revelar que el recurso existe.
- **RLS_Audit_Script**: Script ejecutable como pytest que escanea `app/rutas/` buscando
  violaciones de RLS y endpoints sin autenticación, saliendo con código no-cero ante hallazgos.
- **Multi_Tenant_Property_Test**: Suite de property-based tests con Hypothesis que verifica el
  aislamiento entre tenants en todos los endpoints que retornan o modifican datos multi-tenant.
- **MovimientoCaja**: Entidad de base de datos que registra movimientos económicos del taller.
  Toda query sobre esta entidad debe incluir filtro por `taller_id`.
- **LogNotificacion**: Entidad de base de datos que registra logs de notificaciones WhatsApp.
  Toda query sobre esta entidad debe incluir filtro por `taller_id`.
- **Route_Handler**: Función Python decorada con `@router.get`, `@router.post`, `@router.put`,
  `@router.patch` o `@router.delete` dentro de `app/rutas/`.
- **Multi_Tenant_Table**: Tabla de base de datos que contiene datos operativos de talleres:
  `Ticket`, `MovimientoCaja`, `LogNotificacion`, `Vehiculo`, `Cliente`.

## Requirements

### Requirement 1: Resolver hallazgos críticos de RLS en whatsapp_ruta.py (C-03, C-04, C-05, C-07)

**User Story:** Como administrador de seguridad, quiero que todos los endpoints de WhatsApp
requieran autenticación y filtren datos por taller, para garantizar que ningún taller pueda
acceder a mensajes ni logs de otro taller.

#### Acceptance Criteria

1. WHEN a request reaches POST `/api/mobile/tickets/{id}/whatsapp`, THE RLS_Guard SHALL require
   a valid JWT token via `@require_auth` before processing (resolves C-03)
2. WHEN a request reaches POST `/api/whatsapp/tickets/{id}/mensaje`, THE RLS_Guard SHALL require
   a valid JWT token via `@require_auth` before processing (resolves C-03)
3. WHEN a request reaches GET `/api/mobile/whatsapp/logs`, THE RLS_Guard SHALL require a valid
   JWT token via `@require_auth` before processing (resolves C-04)
4. WHEN a request reaches GET `/api/mobile/whatsapp/logs`, THE RLS_Guard SHALL filter
   `LogNotificacion` records exclusively by `request.state.taller_id` (resolves C-04)
5. WHEN a Twilio webhook payload arrives at POST `/whatsapp/webhook`, THE Webhook_Router SHALL
   extract the `To` field from the payload and route the message to the taller whose registered
   phone number matches that `To` value (resolves C-05)
6. IF no taller is found matching the `To` field in the webhook payload, THEN THE Webhook_Router
   SHALL return HTTP 404 and log the unrouted message (resolves C-05)
7. WHEN processing a ticket action in a WhatsApp endpoint, THE RLS_Guard SHALL verify that
   `ticket.taller_id == request.state.taller_id` before passing the ticket to the service layer
   (resolves C-07)
8. IF `ticket.taller_id != request.state.taller_id`, THEN THE RLS_Guard SHALL return HTTP 404
   without revealing that the ticket exists in another taller (resolves C-07)

### Requirement 2: Resolver hallazgos críticos de RLS en economia_ruta.py (C-06)

**User Story:** Como administrador de seguridad, quiero que todas las queries de economía filtren
por el taller del usuario autenticado, para que los reportes financieros de un taller nunca
incluyan datos de otro taller.

#### Acceptance Criteria

1. THE `_base_query_dia()` helper SHALL accept `taller_id` as a required parameter and apply
   `.filter(MovimientoCaja.taller_id == taller_id)` to every query it constructs (resolves C-06)
2. THE `_sumar_por_tipo()` helper SHALL accept `taller_id` as a required parameter and pass it
   to `_base_query_dia()` without modification (resolves C-06)
3. WHEN any endpoint in `economia_ruta.py` calls `_base_query_dia()` or `_sumar_por_tipo()`,
   THE endpoint SHALL pass `request.state.taller_id` as the `taller_id` argument (resolves C-06)
4. THE `economia_ruta.py` module SHALL NOT contain any query on `MovimientoCaja` without a
   `taller_id` filter (resolves C-06)
5. WHEN a request reaches any endpoint in `economia_ruta.py`, THE RLS_Guard SHALL require a
   valid JWT token via `@require_auth` before processing

### Requirement 3: Resolver hallazgos críticos de RLS en pdf_ruta.py (C-09, A-03)

**User Story:** Como administrador de seguridad, quiero que la generación de PDFs requiera
autenticación y esté restringida al taller del usuario, para que ningún usuario pueda generar
ni descargar PDFs de tickets de otro taller.

#### Acceptance Criteria

1. WHEN a request reaches any endpoint in `pdf_ruta.py`, THE RLS_Guard SHALL require a valid
   JWT token via `@require_auth` before processing (resolves A-03)
2. WHEN `TicketRepository` is instantiated in `pdf_ruta.py`, THE repository SHALL be initialized
   with `taller_id=request.state.taller_id` (resolves C-09)
3. WHEN a PDF generation request is received, THE RLS_Guard SHALL verify that the requested
   ticket belongs to `request.state.taller_id` before generating the PDF (resolves C-09)
4. IF the requested ticket belongs to a different taller, THEN THE RLS_Guard SHALL return
   HTTP 404 without revealing that the ticket exists (resolves C-09)
5. THE `pdf_ruta.py` module SHALL NOT instantiate `TicketRepository` without passing
   `taller_id=request.state.taller_id`

### Requirement 4: Resolver hallazgos de RLS en upload_ruta.py (A-01, A-02)

**User Story:** Como administrador de seguridad, quiero que los endpoints de upload requieran
autenticación y que los archivos solo sean accesibles por el taller al que pertenecen, para
prevenir acceso no autorizado a fotos, comprobantes y firmas.

#### Acceptance Criteria

1. WHEN a request reaches POST `/upload/foto`, THE RLS_Guard SHALL require a valid JWT token
   via `@require_auth` before processing (resolves A-01)
2. WHEN a request reaches POST `/upload/compra`, THE RLS_Guard SHALL require a valid JWT token
   via `@require_auth` before processing (resolves A-01)
3. WHEN a request reaches POST `/upload/firma`, THE RLS_Guard SHALL require a valid JWT token
   via `@require_auth` before processing (resolves A-01)
4. WHEN a file serving request is received, THE RLS_Guard SHALL extract the `taller_id` from
   the file path and verify it matches `request.state.taller_id` (resolves A-02)
5. IF the `taller_id` in the file path does not match `request.state.taller_id`, THEN THE
   RLS_Guard SHALL return HTTP 404 without revealing that the file exists (resolves A-02)
6. WHEN a file serving request is received without a valid JWT token, THE RLS_Guard SHALL
   return HTTP 401 (resolves A-02)

### Requirement 5: Resolver antipatrones de autenticación (M-01, M-02, M-03)

**User Story:** Como administrador de seguridad, quiero que todos los endpoints que acceden a
datos del taller tengan `@require_auth` explícito, para eliminar cualquier endpoint que pueda
ser accedido sin autenticación por omisión o error de configuración.

#### Acceptance Criteria

1. WHEN a request reaches `cambiar_password_admin` in `seguridad_ruta.py`, THE RLS_Guard SHALL
   require a valid JWT token via `@require_auth` before processing (resolves M-01)
2. WHEN a request reaches any endpoint in `ticket_ruta.py` that reads or writes ticket data,
   THE RLS_Guard SHALL require a valid JWT token via `@require_auth` before processing
   (resolves M-02)
3. WHEN a request reaches `listar_mecanicos` in `configuracion_ruta.py`, THE RLS_Guard SHALL
   require a valid JWT token via `@require_auth` before processing (resolves M-03)
4. IF a request reaches any of the above endpoints without a valid JWT token, THEN THE system
   SHALL return HTTP 401 with a generic error message
5. THE `@require_auth` decorator SHALL be declared explicitly on each endpoint function — no
   endpoint SHALL rely on inherited or implicit authentication from a parent router

### Requirement 6: Script de auditoría automática de RLS

**User Story:** Como desarrollador del sistema, quiero un script de auditoría automatizada que
detecte violaciones de RLS antes del despliegue, para que ningún hallazgo de este tipo llegue
a producción sin ser detectado.

#### Acceptance Criteria

1. THE RLS_Audit_Script SHALL scan all Python files in `app/rutas/` for Route_Handler functions
2. WHEN the RLS_Audit_Script finds a Route_Handler that queries a Multi_Tenant_Table (`Ticket`,
   `MovimientoCaja`, `LogNotificacion`, `Vehiculo`, `Cliente`) without a `taller_id` filter,
   THE script SHALL report it as a critical violation with file path, line number, and description
3. WHEN the RLS_Audit_Script finds a Route_Handler decorated with `@router.get`, `@router.post`,
   `@router.put`, `@router.patch`, or `@router.delete` without `@require_auth` in its decorator
   chain, THE script SHALL report it as a high violation with file path, line number, and description
4. THE RLS_Audit_Script SHALL generate a report listing: file path, line number, violation
   severity (critical/high), and a human-readable description of the violation
5. WHEN the RLS_Audit_Script finds one or more critical or high violations, THE script SHALL
   exit with a non-zero status code
6. THE RLS_Audit_Script SHALL be executable as a pytest test via
   `pytest tests/test_rls_audit.py` without additional configuration
7. THE RLS_Audit_Script SHALL complete its scan of `app/rutas/` in under 10 seconds

### Requirement 7: Property-Based Testing para aislamiento multi-tenant

**User Story:** Como desarrollador del sistema, quiero tests de property-based testing que
validen el aislamiento multi-tenant en todos los endpoints, para garantizar con alta confianza
estadística que ningún usuario puede acceder a datos de otro taller.

#### Acceptance Criteria

1. THE Multi_Tenant_Property_Test SHALL use Hypothesis to generate random valid JWT tokens for
   at least two different `taller_id` values per test run
2. THE Multi_Tenant_Property_Test SHALL verify that a request authenticated with `taller_id=A`
   never receives a response body containing any resource with `taller_id=B` where `A != B`
3. THE Multi_Tenant_Property_Test SHALL cover all GET endpoints in `app/rutas/` that return
   multi-tenant data (tickets, movimientos, logs, vehículos, clientes, PDFs, archivos)
4. THE Multi_Tenant_Property_Test SHALL cover all POST, PUT, PATCH endpoints to verify that
   created or updated resources are assigned `taller_id = request.state.taller_id`
5. THE Multi_Tenant_Property_Test SHALL execute at least 100 random combinations of
   `(endpoint, taller_id_requester, taller_id_resource)` per test run
6. WHEN the Multi_Tenant_Property_Test detects a cross-tenant data leak, THE test SHALL fail
   with a message that includes: the endpoint URL, the `taller_id` used in the request, and
   the `taller_id` found in the response data

## Correctness Properties for Property-Based Testing

### Property 1: Aislamiento Multi-Tenant (Cross-Tenant Isolation)

Para todo request autenticado con `taller_id=A`, el sistema nunca retorna en el cuerpo de la
respuesta ningún recurso cuyo `taller_id` sea `B`, donde `A ≠ B`.

Formalmente: `∀ (endpoint, taller_id_A, taller_id_B, resource_id) donde A ≠ B:`
`response(endpoint, auth=JWT(taller_id=A)).body` no contiene ningún objeto con `taller_id=B`

**Tipo:** Property-based test (Hypothesis, ≥100 combinaciones)
**Aplica a:** Requirements 1, 2, 3, 4 — todos los endpoints que retornan datos multi-tenant

### Property 2: Integridad de taller_id en escrituras

Para todo endpoint que crea o actualiza recursos, el recurso resultante tiene
`taller_id = request.state.taller_id` — nunca un `taller_id` diferente al del JWT.

Formalmente: `∀ (endpoint, method, taller_id_A) donde method ∈ {POST, PUT, PATCH}:`
`resource_created_by(endpoint, auth=JWT(taller_id=A)).taller_id == A`

**Tipo:** Property-based test (Hypothesis, variando endpoint y taller_id)
**Aplica a:** Requirements 1, 2, 3, 4 — todos los endpoints que crean o modifican datos multi-tenant
