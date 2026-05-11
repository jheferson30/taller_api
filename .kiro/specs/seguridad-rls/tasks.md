# Implementation Plan: Seguridad RLS — Hallazgos de Auditoría

## Overview

This implementation plan addresses 12 critical, high, and medium severity Row-Level Security (RLS) violations identified in the security audit. The plan follows a 7-phase approach: Infrastructure setup, then systematic fixes across WhatsApp, Economia, PDF, Upload, and Miscellaneous routes, followed by comprehensive verification.

**Key Security Invariant:** Every authenticated request must filter all multi-tenant data by `request.state.taller_id` extracted from the JWT token. The `taller_id` must NEVER come from request body, query parameters, or headers provided by the client.

**Implementation Language:** Python (FastAPI + SQLAlchemy)

## Tasks

- [x] 1. Phase 1: Infrastructure Setup — RLS Audit Script and Property-Based Tests
  - [x] 1.1 Create RLS audit script foundation
    - Create `scripts/rls_audit.py` with `RLSAuditor` class
    - Implement AST-based scanning for route files in `app/rutas/`
    - Define `RLSViolation` dataclass with fields: file_path, line_number, severity, violation_type, description, code_snippet
    - _Requirements: 6.1, 6.2, 6.3_

  - [x] 1.2 Implement violation detection rules in audit script
    - Implement CRITICAL detection: queries on multi-tenant tables (`Ticket`, `MovimientoCaja`, `LogNotificacion`, `Vehiculo`, `Cliente`) without `taller_id` filter
    - Implement HIGH detection: route handlers without `@require_auth` decorator
    - Implement HIGH detection: repository instantiation without `taller_id` parameter
    - Generate human-readable report with file path, line number, severity, and description
    - _Requirements: 6.2, 6.3, 6.4_

  - [x] 1.3 Make audit script executable and integrate with pytest
    - Add CLI interface to `scripts/rls_audit.py` with exit code handling
    - Create `tests/test_rls_audit.py` wrapper that runs audit and fails on violations
    - Ensure script completes scan in under 10 seconds
    - _Requirements: 6.5, 6.6, 6.7_

  - [x] 1.4 Create property-based test foundation
    - Create `tests/test_rls_properties.py` with Hypothesis configuration
    - Implement JWT token generation helper for testing with configurable `taller_id`
    - Implement test data factory for creating resources with specific `taller_id`
    - Configure Hypothesis for minimum 100 iterations per property test
    - _Requirements: 7.1, 7.5_

  - [x] 1.5 Write property test for cross-tenant isolation (Property 1)
    - **Property 1: Cross-Tenant Isolation**
    - **Validates: Requirements 1, 2, 3, 4**
    - Implement property test that generates random `taller_id_requester` and `taller_id_resource`
    - Test all GET endpoints that return multi-tenant data
    - Verify that requests with `taller_id=A` never receive resources with `taller_id=B` where A ≠ B
    - Verify cross-tenant access returns HTTP 404 (not 403)
    - _Requirements: 7.2, 7.3, 7.6_

  - [x] 1.6 Write property test for write integrity (Property 2)
    - **Property 2: Write Integrity**
    - **Validates: Requirements 1, 2, 3, 4**
    - Implement property test that generates random `taller_id_jwt` and `taller_id_payload`
    - Test all POST, PUT, PATCH endpoints that create or update resources
    - Verify created/updated resources have `taller_id = request.state.taller_id` from JWT
    - Verify system ignores `taller_id` from request body/params
    - _Requirements: 7.4, 7.6_

  - [x] 1.7 Run baseline audit to document current violations
    - Execute `pytest tests/test_rls_audit.py` to establish baseline
    - Document all 12 violations found (C-03, C-04, C-05, C-06, C-07, C-09, A-01, A-02, A-03, M-01, M-02, M-03)
    - Save baseline report for comparison after fixes
    - _Requirements: 6.4, 6.5_

- [x] 2. Checkpoint — Infrastructure Ready
  - Ensure all tests pass, ask the user if questions arise.

- [x] 3. Phase 2: Fix WhatsApp Routes (Requirement 1)
  - [x] 3.1 Add authentication to WhatsApp send endpoints (C-03)
    - Add `@require_auth` decorator to POST `/api/mobile/tickets/{id}/whatsapp` in `app/rutas/whatsapp_ruta.py` line ~70
    - Add `@require_auth` decorator to POST `/api/whatsapp/tickets/{id}/mensaje` in `app/rutas/whatsapp_ruta.py` line ~88
    - Verify both endpoints extract `taller_id` from `request.state.taller_id`
    - _Requirements: 1.1, 1.2_

  - [x] 3.2 Add authentication and RLS filter to WhatsApp logs endpoint (C-04)
    - Add `@require_auth` decorator to GET `/api/mobile/whatsapp/logs` in `app/rutas/whatsapp_ruta.py` line ~109
    - Add `taller_id` filter to `LogNotificacion` query: `.filter(LogNotificacion.taller_id == request.state.taller_id)`
    - Verify endpoint returns only logs belonging to authenticated user's taller
    - _Requirements: 1.3, 1.4_

  - [x] 3.3 Implement webhook routing for multi-tenant WhatsApp messages (C-05)
    - Create `WebhookRouter` class in `app/servicios/whatsapp_servicio.py`
    - Implement `route_whatsapp_message(payload: dict) -> tuple[int | None, str]` method
    - Extract `To` field from Twilio webhook payload (WhatsApp Business phone number)
    - Query `talleres` table: `SELECT id FROM talleres WHERE whatsapp_phone_number = To`
    - Return `(taller_id, phone_number)` if found, `(None, phone_number)` if not found
    - _Requirements: 1.5, 1.6_

  - [x] 3.4 Handle unrouted webhook messages (C-05)
    - Update POST `/whatsapp/webhook` in `app/rutas/whatsapp_ruta.py` line ~47 to use `WebhookRouter`
    - If `taller_id` is None, return HTTP 404 with generic message
    - Log unrouted messages with phone number and payload to separate table or log file
    - Add warning log entry for investigation
    - _Requirements: 1.6_

  - [x] 3.5 Add ticket ownership verification for WhatsApp operations (C-07)
    - In WhatsApp send endpoints, after fetching ticket, verify `ticket.taller_id == request.state.taller_id`
    - If mismatch, return HTTP 404 with message "Resource not found" (don't reveal ticket exists)
    - Apply verification in both POST `/api/mobile/tickets/{id}/whatsapp` and POST `/api/whatsapp/tickets/{id}/mensaje`
    - _Requirements: 1.7, 1.8_

  - [x] 3.6 Write unit tests for WhatsApp route fixes
    - Test POST `/api/mobile/tickets/{id}/whatsapp` without JWT → 401
    - Test POST `/api/whatsapp/tickets/{id}/mensaje` without JWT → 401
    - Test GET `/api/mobile/whatsapp/logs` without JWT → 401
    - Test GET `/api/mobile/whatsapp/logs` returns only logs for authenticated taller
    - Test cross-tenant ticket access in WhatsApp endpoints → 404
    - Test webhook routing with registered phone → routes to correct taller
    - Test webhook routing with unregistered phone → 404 and logged
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8_

- [x] 4. Checkpoint — WhatsApp Routes Secured
  - Ensure all tests pass, ask the user if questions arise.

- [x] 5. Phase 3: Fix Economia Routes (Requirement 2)
  - [x] 5.1 Add taller_id parameter to _base_query_dia helper (C-06)
    - Modify `_base_query_dia(db: Session, fecha_objetivo: date)` in `app/rutas/economia_ruta.py` line ~20
    - Add `taller_id: int` as required parameter
    - Add filter: `.filter(MovimientoCaja.taller_id == taller_id)` to all queries constructed by this helper
    - _Requirements: 2.1_

  - [x] 5.2 Add taller_id parameter to _sumar_por_tipo helper (C-06)
    - Modify `_sumar_por_tipo(db: Session, fecha_objetivo: date, tipo: str)` in `app/rutas/economia_ruta.py`
    - Add `taller_id: int` as required parameter
    - Pass `taller_id` to `_base_query_dia()` calls without modification
    - _Requirements: 2.2_

  - [x] 5.3 Update all economia endpoints to pass taller_id from JWT (C-06)
    - Identify all endpoints in `app/rutas/economia_ruta.py` that call `_base_query_dia()` or `_sumar_por_tipo()`
    - Extract `taller_id = request.state.taller_id` in each endpoint
    - Pass `taller_id` as argument to helper functions
    - _Requirements: 2.3_

  - [x] 5.4 Add authentication to all economia endpoints (C-06)
    - Add `@require_auth` decorator to all endpoints in `app/rutas/economia_ruta.py`
    - Verify no endpoint queries `MovimientoCaja` without `taller_id` filter
    - _Requirements: 2.4, 2.5_

  - [x] 5.5 Write unit tests for economia route fixes
    - Test all economia endpoints without JWT → 401
    - Test economia reports return only data for authenticated taller
    - Test cross-tenant MovimientoCaja access → empty results or 404
    - Test `_base_query_dia` includes taller_id filter in generated SQL
    - Test `_sumar_por_tipo` passes taller_id correctly
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_

- [x] 6. Checkpoint — Economia Routes Secured
  - Ensure all tests pass, ask the user if questions arise.

- [x] 7. Phase 4: Fix PDF Routes (Requirement 3)
  - [x] 7.1 Add authentication to all PDF endpoints (A-03)
    - Add `@require_auth` decorator to all endpoints in `app/rutas/pdf_ruta.py` (lines ~20, ~61, ~109)
    - Verify all PDF generation endpoints require valid JWT token
    - _Requirements: 3.1_

  - [x] 7.2 Fix TicketRepository instantiation with taller_id (C-09)
    - Locate all `TicketRepository` instantiations in `app/rutas/pdf_ruta.py` line ~43
    - Change from `TicketRepository(db)` to `TicketRepository(db, taller_id=request.state.taller_id)`
    - Verify repository filters tickets by taller_id automatically
    - _Requirements: 3.2, 3.5_

  - [x] 7.3 Add ticket ownership verification before PDF generation (C-09)
    - After fetching ticket for PDF generation, verify `ticket.taller_id == request.state.taller_id`
    - If mismatch, return HTTP 404 with message "Resource not found"
    - Apply to all PDF generation endpoints
    - _Requirements: 3.3, 3.4_

  - [x] 7.4 Write unit tests for PDF route fixes
    - Test all PDF endpoints without JWT → 401
    - Test PDF generation for ticket from different taller → 404
    - Test PDF generation for own ticket → 200 with PDF content
    - Test TicketRepository instantiation includes taller_id parameter
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

- [x] 8. Checkpoint — PDF Routes Secured
  - Ensure all tests pass, ask the user if questions arise.

- [x] 9. Phase 5: Fix Upload Routes (Requirement 4)
  - [x] 9.1 Add authentication to upload endpoints (A-01)
    - Add `@require_auth` decorator to POST `/upload/foto` in `app/rutas/upload_ruta.py` line ~32
    - Add `@require_auth` decorator to POST `/upload/compra` in `app/rutas/upload_ruta.py` line ~61
    - Add `@require_auth` decorator to POST `/upload/firma` in `app/rutas/upload_ruta.py` line ~89
    - _Requirements: 4.1, 4.2, 4.3_

  - [x] 9.2 Add authentication to file serving endpoints (A-02)
    - Add `@require_auth` decorator to GET `/uploads/fotos/{filename}` in `app/rutas/upload_ruta.py` line ~117
    - Add `@require_auth` decorator to GET `/uploads/compras/{filename}` in `app/rutas/upload_ruta.py` line ~127
    - Add `@require_auth` decorator to GET `/uploads/firmas/{filename}` in `app/rutas/upload_ruta.py` line ~137
    - _Requirements: 4.6_

  - [x] 9.3 Implement taller_id verification for file serving (A-02)
    - In file serving endpoints, extract `taller_id` from file path (format: `uploads/talleres/{taller_id}/tipo/filename`)
    - Verify extracted `taller_id` matches `request.state.taller_id`
    - If mismatch, return HTTP 404 with message "File not found"
    - Apply to all three file serving endpoints
    - _Requirements: 4.4, 4.5_

  - [x] 9.4 Write unit tests for upload route fixes
    - Test POST `/upload/foto` without JWT → 401
    - Test POST `/upload/compra` without JWT → 401
    - Test POST `/upload/firma` without JWT → 401
    - Test GET file from different taller → 404
    - Test GET file from own taller → 200 with file content
    - Test file path parsing extracts taller_id correctly
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6_

- [x] 10. Checkpoint — Upload Routes Secured
  - Ensure all tests pass, ask the user if questions arise.

- [x] 11. Phase 6: Fix Miscellaneous Routes (Requirement 5)
  - [x] 11.1 Add authentication to cambiar_password_admin endpoint (M-01)
    - Add `@require_auth` decorator to `cambiar_password_admin` in `app/rutas/seguridad_ruta.py` line ~161
    - Verify endpoint requires valid JWT token before processing
    - _Requirements: 5.1_

  - [x] 11.2 Add authentication to ticket_ruta.py endpoints (M-02)
    - Scan all endpoints in `app/rutas/ticket_ruta.py` that read or write ticket data
    - Add `@require_auth` decorator to any endpoint missing it
    - Verify all ticket operations require authentication
    - _Requirements: 5.2_

  - [x] 11.3 Add authentication to listar_mecanicos endpoint (M-03)
    - Add `@require_auth` decorator to `listar_mecanicos` in `app/rutas/configuracion_ruta.py` line ~54
    - Verify endpoint requires valid JWT token before processing
    - _Requirements: 5.3_

  - [x] 11.4 Verify explicit @require_auth on all fixed endpoints
    - Review all endpoints modified in this phase
    - Ensure `@require_auth` is declared explicitly on each function (not inherited)
    - Verify endpoints return HTTP 401 with generic message when JWT is missing
    - _Requirements: 5.4, 5.5_

  - [x] 11.5 Write unit tests for miscellaneous route fixes
    - Test `cambiar_password_admin` without JWT → 401
    - Test all ticket_ruta.py endpoints without JWT → 401
    - Test `listar_mecanicos` without JWT → 401
    - Test all endpoints with valid JWT → 200 or appropriate success code
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

- [x] 12. Checkpoint — All Routes Secured
  - Ensure all tests pass, ask the user if questions arise.

- [x] 13. Phase 7: Verification and Final Audit
  - [x] 13.1 Run RLS audit script on fixed codebase
    - Execute `pytest tests/test_rls_audit.py`
    - Verify audit reports 0 critical violations (down from 7)
    - Verify audit reports 0 high violations (down from 3)
    - Verify audit reports 0 medium violations (down from 2)
    - _Requirements: 6.4, 6.5_

  - [x] 13.2 Run property-based tests for tenant isolation
    - Execute `pytest tests/test_rls_properties.py`
    - Verify Property 1 (Cross-Tenant Isolation) passes 100+ iterations
    - Verify Property 2 (Write Integrity) passes 100+ iterations
    - Review any failures and fix underlying issues
    - _Requirements: 7.2, 7.3, 7.4, 7.5, 7.6_

  - [x] 13.3 Run integration tests for end-to-end flows
    - Test complete ticket workflow: create as taller_id=1, view as taller_id=2 → 404
    - Test WhatsApp webhook flow: send message to registered phone → routes correctly
    - Test economia report flow: create movimientos for taller_id=1, generate report as taller_id=2 → empty
    - Test PDF generation flow: generate PDF for ticket from different taller → 404
    - Test file upload/download flow: upload as taller_id=1, download as taller_id=2 → 404
    - _Requirements: 1, 2, 3, 4, 5_

  - [x] 13.4 Manual security review of all modified files
    - Review `app/rutas/whatsapp_ruta.py` for RLS compliance
    - Review `app/rutas/economia_ruta.py` for RLS compliance
    - Review `app/rutas/pdf_ruta.py` for RLS compliance
    - Review `app/rutas/upload_ruta.py` for RLS compliance
    - Review `app/rutas/seguridad_ruta.py` for RLS compliance
    - Review `app/rutas/ticket_ruta.py` for RLS compliance
    - Review `app/rutas/configuracion_ruta.py` for RLS compliance
    - Verify all endpoints have `@require_auth` decorator
    - Verify all queries filter by `taller_id` from `request.state`
    - Verify cross-tenant access returns 404 (not 403)
    - _Requirements: 1, 2, 3, 4, 5_

  - [x] 13.5 Document security improvements and remaining limitations
    - Create summary document listing all 12 violations fixed
    - Document known limitation: models without `taller_id` columns (out of scope)
    - Document workaround strategy: application-layer RLS via related entities
    - Update security documentation with new RLS audit script usage
    - Add property-based testing documentation for future development
    - _Requirements: 6, 7_

- [x] 14. Final Checkpoint — Implementation Complete
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation after each phase
- Property tests validate universal correctness properties (Property 1: Cross-Tenant Isolation, Property 2: Write Integrity)
- Unit tests validate specific examples and edge cases
- The audit script runs in CI/CD to prevent future RLS violations
- All fixes maintain backward compatibility with existing API contracts
- Cross-tenant access attempts return HTTP 404 (not 403) to avoid revealing resource existence
- SUPER_ADMIN users (taller_id=null) are blocked from tenant endpoints with HTTP 403
