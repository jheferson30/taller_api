# Design Document: Seguridad RLS — Hallazgos de Auditoría

## Overview

This design addresses critical Row-Level Security (RLS) violations identified in the security audit of a multi-tenant SaaS workshop management system. The system currently has 12 critical/high/medium severity findings across 7 route files where endpoints either lack authentication or fail to filter data by `taller_id`, creating cross-tenant data leakage risks.

**Core Security Invariant:** Every authenticated request must filter all multi-tenant data by `request.state.taller_id` extracted from the JWT token. The `taller_id` must NEVER come from request body, query parameters, or headers provided by the client.

**Scope:**
- Fix 12 RLS violations across 7 route files
- Implement webhook routing for multi-tenant WhatsApp messages
- Create automated RLS audit script
- Implement property-based tests for tenant isolation

**Out of Scope:**
- Database schema changes (models already exist without `taller_id` — this is a known limitation)
- Implementing `taller_id` columns in existing tables
- Refactoring existing TenantRepository pattern

## Architecture

### Current State

The system has partial RLS infrastructure:
- **AuthMiddleware**: Validates JWT tokens and injects `request.state.user` and `request.state.taller_id`
- **@require_auth decorator**: Validates that `request.state.user` exists
- **@require_role decorator**: Validates user has required roles
- **TenantRepository base class**: Provides automatic `taller_id` filtering for repositories that inherit from it
- **Legacy authentication**: Some endpoints use `X-Admin-Password` header instead of JWT

**Problem:** Many endpoints bypass these mechanisms:
1. Missing `@require_auth` decorators (endpoints accessible without authentication)
2. Direct database queries without `taller_id` filters
3. Repositories instantiated without passing `taller_id`
4. Webhook routing that doesn't determine which tenant owns incoming messages

### Target Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     FastAPI Request                          │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              AuthMiddleware (JWT Validation)                 │
│  • Validates JWT token                                       │
│  • Injects request.state.user                                │
│  • Injects request.state.taller_id                           │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│           Route Handler (@require_auth decorator)            │
│  • Validates authentication                                  │
│  • Extracts taller_id from request.state                     │
│  • Passes taller_id to service/repository layer              │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              Service Layer (Business Logic)                  │
│  • Receives taller_id as parameter                           │
│  • Validates business rules                                  │
│  • Calls repository with taller_id                           │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│         Repository Layer (Data Access + RLS Filter)          │
│  • Applies .filter(Model.taller_id == taller_id)             │
│  • Returns only data belonging to tenant                     │
│  • Returns 404 for cross-tenant access attempts              │
└─────────────────────────────────────────────────────────────┘
```

**Special Case: Webhook Routing**

```
┌─────────────────────────────────────────────────────────────┐
│           Twilio WhatsApp Webhook (Unauthenticated)          │
│  POST /whatsapp/webhook                                      │
│  Body: { "entry": [{ "changes": [{ "value": {               │
│    "messages": [{ "from": "+573001234567" }],                │
│    "metadata": { "phone_number_id": "123" }                  │
│  }}]}]}                                                      │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                  Webhook Router Logic                        │
│  1. Extract "To" field from payload                          │
│  2. Query: SELECT taller_id FROM talleres                    │
│            WHERE whatsapp_phone_number = "To"                │
│  3. If found: route message to that taller                   │
│  4. If not found: return 404 and log unrouted message        │
└─────────────────────────────────────────────────────────────┘
```

## Components and Interfaces

### 1. RLS Guard Decorator (New)

**Purpose:** Centralized decorator that combines authentication and tenant verification.

**Interface:**
```python
def require_rls_guard(func: Callable) -> Callable:
    """
    Decorator that enforces RLS by:
    1. Requiring authentication (@require_auth)
    2. Extracting taller_id from request.state
    3. Validating taller_id is not None
    
    Usage:
        @router.get("/tickets")
        @require_rls_guard
        async def list_tickets(request: Request, db: Session = Depends(obtener_db)):
            taller_id = request.state.taller_id
            # Use taller_id in queries
    """
```

**Implementation Strategy:**
- Wraps existing `@require_auth` decorator
- Adds validation that `request.state.taller_id` is not None
- Returns HTTP 401 if taller_id is missing (indicates JWT without tenant context)

### 2. Webhook Router (New)

**Purpose:** Route incoming WhatsApp messages to the correct tenant.

**Interface:**
```python
class WebhookRouter:
    def __init__(self, db: Session):
        self.db = db
    
    def route_whatsapp_message(self, payload: dict) -> tuple[int | None, str]:
        """
        Determines which taller owns an incoming WhatsApp message.
        
        Args:
            payload: Twilio webhook payload
            
        Returns:
            tuple: (taller_id, phone_number) or (None, phone_number) if not found
        """
```

**Routing Logic:**
1. Extract `To` field from webhook payload (the WhatsApp Business phone number that received the message)
2. Query `talleres` table: `SELECT id FROM talleres WHERE whatsapp_phone_number = To`
3. If found: return `taller_id`
4. If not found: return `None` and log unrouted message

### 3. RLS Audit Script (New)

**Purpose:** Static analysis tool that scans route files for RLS violations.

**Interface:**
```python
class RLSAuditor:
    def scan_routes(self, routes_dir: str) -> list[RLSViolation]:
        """
        Scans all Python files in routes_dir for RLS violations.
        
        Returns:
            List of violations with file, line, severity, description
        """
    
    def generate_report(self, violations: list[RLSViolation]) -> str:
        """
        Generates human-readable report of violations.
        """
```

**Detection Rules:**
1. **Critical:** Query on multi-tenant table without `taller_id` filter
   - Pattern: `db.query(Ticket|MovimientoCaja|LogNotificacion|Vehiculo|Cliente).filter(...)`
   - Missing: `.filter(Model.taller_id == taller_id)`

2. **High:** Route handler without `@require_auth` decorator
   - Pattern: `@router.(get|post|put|patch|delete)` without `@require_auth` in decorator chain

3. **High:** Repository instantiation without `taller_id` parameter
   - Pattern: `TicketRepository(db)` should be `TicketRepository(db, taller_id)`

### 4. Modified Route Handlers

**Pattern for all fixed endpoints:**
```python
@router.get("/api/endpoint")
@require_auth  # NEW: Add authentication
@limiter.limit("30/minute")
async def endpoint_handler(
    request: Request,
    db: Session = Depends(obtener_db)
):
    # NEW: Extract taller_id from JWT
    taller_id = request.state.taller_id
    
    # NEW: Pass taller_id to all queries
    query = db.query(Model).filter(Model.taller_id == taller_id)
    
    # NEW: Verify resource ownership before returning
    resource = query.filter(Model.id == resource_id).first()
    if not resource:
        raise HTTPException(status_code=404, detail="Resource not found")
    
    return resource
```

### 5. Modified Helper Functions (economia_ruta.py)

**Current (Vulnerable):**
```python
def _base_query_dia(db: Session, fecha_objetivo: date):
    return db.query(MovimientoCaja).filter(
        func.date(MovimientoCaja.fecha_creacion) == fecha_objetivo
    )
```

**Fixed:**
```python
def _base_query_dia(db: Session, fecha_objetivo: date, taller_id: int):
    return db.query(MovimientoCaja).filter(
        MovimientoCaja.taller_id == taller_id,
        func.date(MovimientoCaja.fecha_creacion) == fecha_objetivo
    )
```

## Data Models

### Existing Models (No Changes Required)

**Note:** The requirements document indicates that `Ticket`, `MovimientoCaja`, `LogNotificacion`, `Vehiculo`, and `Cliente` are multi-tenant tables. However, inspection of the codebase reveals that these models **do not currently have `taller_id` columns**. This is a known limitation that is out of scope for this spec.

**Workaround Strategy:**
- For models without `taller_id`, we will implement RLS at the application layer by:
  1. Requiring authentication on all endpoints
  2. Validating resource ownership through related entities (e.g., `ticket.vehiculo.taller_id`)
  3. Using service layer validation to prevent cross-tenant access

**Models Requiring RLS (Application-Level):**
- `Ticket`: No `taller_id` column — validate via `vehiculo.taller_id`
- `MovimientoCaja`: No `taller_id` column — validate via `ticket.taller_id`
- `LogNotificacion`: No `taller_id` column — validate via `ticket.taller_id`
- `Vehiculo`: No `taller_id` column — needs migration to add column (out of scope)
- `Cliente`: Not found in codebase

### New Models

**RLSViolation (Audit Script Output):**
```python
@dataclass
class RLSViolation:
    file_path: str
    line_number: int
    severity: Literal["CRITICAL", "HIGH", "MEDIUM"]
    violation_type: str
    description: str
    code_snippet: str
```

## Error Handling

### Cross-Tenant Access Attempts

**Requirement:** Return HTTP 404 (not 403) to avoid revealing that a resource exists in another tenant.

**Implementation:**
```python
# ✅ CORRECT
resource = db.query(Model).filter(
    Model.id == resource_id,
    Model.taller_id == taller_id
).first()

if not resource:
    raise HTTPException(status_code=404, detail="Resource not found")

# ❌ INCORRECT (reveals resource exists)
resource = db.query(Model).filter(Model.id == resource_id).first()
if not resource:
    raise HTTPException(status_code=404, detail="Resource not found")
if resource.taller_id != taller_id:
    raise HTTPException(status_code=403, detail="Access denied")
```

### Missing taller_id in JWT

**Scenario:** SUPER_ADMIN users have `taller_id = null` in their JWT.

**Handling:**
```python
@router.get("/api/endpoint")
@require_auth
async def endpoint_handler(request: Request, db: Session = Depends(obtener_db)):
    taller_id = request.state.taller_id
    
    if taller_id is None:
        raise HTTPException(
            status_code=403,
            detail="This endpoint requires a tenant context. SUPER_ADMIN cannot access tenant data."
        )
```

### Webhook Routing Failures

**Scenario:** Incoming WhatsApp message for unregistered phone number.

**Handling:**
```python
taller_id, phone_number = webhook_router.route_whatsapp_message(payload)

if taller_id is None:
    logger.warning(f"Unrouted WhatsApp message from {phone_number}")
    # Log to separate table for investigation
    db.add(UnroutedMessage(
        phone_number=phone_number,
        payload=json.dumps(payload),
        timestamp=datetime.now()
    ))
    db.commit()
    return JSONResponse(status_code=404, content={"status": "unrouted"})
```

### Audit Script Failures

**Scenario:** Audit script finds violations.

**Handling:**
```python
def test_rls_audit():
    auditor = RLSAuditor()
    violations = auditor.scan_routes("app/rutas/")
    
    if violations:
        report = auditor.generate_report(violations)
        pytest.fail(f"RLS violations found:\n{report}")
```

## Testing Strategy

### Unit Tests

**Focus:** Specific examples and edge cases for each fixed endpoint.

**Examples:**
1. **Authentication Tests:**
   - Request without JWT → 401
   - Request with invalid JWT → 401
   - Request with expired JWT → 401
   - Request with valid JWT → 200

2. **Cross-Tenant Access Tests:**
   - User from taller_id=1 requests resource from taller_id=2 → 404
   - User from taller_id=1 requests own resource → 200

3. **Webhook Routing Tests:**
   - Message to registered phone → routes to correct taller
   - Message to unregistered phone → 404 and logged
   - Malformed webhook payload → 400

4. **Audit Script Tests:**
   - Scan file with violations → detects all violations
   - Scan file without violations → returns empty list
   - Generate report → formats correctly

### Property-Based Tests (Hypothesis)

**Property 1: Cross-Tenant Isolation (Requirement 7, Property 1)**

*For any* authenticated request with `taller_id=A`, the system never returns in the response body any resource whose `taller_id` is `B`, where `A ≠ B`.

**Implementation:**
```python
from hypothesis import given, strategies as st
import pytest

@given(
    taller_id_requester=st.integers(min_value=1, max_value=100),
    taller_id_resource=st.integers(min_value=1, max_value=100),
    endpoint=st.sampled_from([
        "/api/mobile/whatsapp/logs",
        "/economia-dia",
        "/tickets/{id}",
        # ... all GET endpoints
    ])
)
def test_cross_tenant_isolation(
    taller_id_requester,
    taller_id_resource,
    endpoint,
    client,
    db
):
    # Arrange: Create resource belonging to taller_id_resource
    resource = create_test_resource(db, taller_id=taller_id_resource)
    
    # Act: Request resource with JWT for taller_id_requester
    jwt_token = generate_jwt(taller_id=taller_id_requester)
    response = client.get(
        endpoint.format(id=resource.id),
        headers={"Authorization": f"Bearer {jwt_token}"}
    )
    
    # Assert: If taller_id_requester != taller_id_resource, must return 404
    if taller_id_requester != taller_id_resource:
        assert response.status_code == 404
        assert "taller_id" not in str(response.json())  # Don't leak tenant info
    else:
        assert response.status_code == 200
        # Verify response contains only resources from taller_id_requester
        response_data = response.json()
        if isinstance(response_data, list):
            for item in response_data:
                if "taller_id" in item:
                    assert item["taller_id"] == taller_id_requester
```

**Configuration:**
- Minimum 100 iterations per property test
- Tag format: `# Feature: seguridad-rls, Property 1: Cross-tenant isolation`

**Property 2: Write Integrity (Requirement 7, Property 2)**

*For any* endpoint that creates or updates resources, the resulting resource has `taller_id = request.state.taller_id` — never a different `taller_id` than the JWT.

**Implementation:**
```python
@given(
    taller_id_jwt=st.integers(min_value=1, max_value=100),
    taller_id_payload=st.integers(min_value=1, max_value=100),
    endpoint=st.sampled_from([
        "/tickets",
        "/tickets/{id}/procesos",
        "/tickets/{id}/repuestos",
        # ... all POST/PUT/PATCH endpoints
    ])
)
def test_write_integrity(
    taller_id_jwt,
    taller_id_payload,
    endpoint,
    client,
    db
):
    # Arrange: Create JWT with taller_id_jwt
    jwt_token = generate_jwt(taller_id=taller_id_jwt)
    
    # Act: Attempt to create resource with taller_id_payload in body
    payload = {
        "taller_id": taller_id_payload,  # Malicious attempt
        "name": "Test Resource"
    }
    response = client.post(
        endpoint,
        json=payload,
        headers={"Authorization": f"Bearer {jwt_token}"}
    )
    
    # Assert: Created resource must have taller_id from JWT, not payload
    if response.status_code in (200, 201):
        created_resource = response.json()
        # Verify taller_id matches JWT, not payload
        resource_from_db = db.query(Model).filter(Model.id == created_resource["id"]).first()
        assert resource_from_db.taller_id == taller_id_jwt
        assert resource_from_db.taller_id != taller_id_payload or taller_id_jwt == taller_id_payload
```

### Integration Tests

**Focus:** End-to-end flows with real database and authentication.

**Examples:**
1. **Complete Ticket Workflow:**
   - Create ticket as taller_id=1
   - Add proceso as taller_id=1 → success
   - Attempt to view ticket as taller_id=2 → 404
   - Attempt to add proceso as taller_id=2 → 404

2. **WhatsApp Webhook Flow:**
   - Register taller with phone number
   - Send webhook message to that number → routes correctly
   - Send webhook message to different number → 404

3. **Economia Report Flow:**
   - Create movimientos for taller_id=1
   - Generate report as taller_id=1 → includes only taller_id=1 data
   - Generate report as taller_id=2 → empty (no cross-tenant data)

### Audit Script Tests

**Focus:** Verify audit script detects all violation types.

**Test Files:**
```python
# tests/fixtures/rls_violations/critical_missing_filter.py
@router.get("/vulnerable")
async def vulnerable_endpoint(db: Session = Depends(obtener_db)):
    # CRITICAL: Missing taller_id filter
    tickets = db.query(Ticket).all()
    return tickets

# tests/fixtures/rls_violations/high_missing_auth.py
@router.get("/unprotected")
async def unprotected_endpoint(db: Session = Depends(obtener_db)):
    # HIGH: Missing @require_auth
    return {"data": "sensitive"}

# tests/fixtures/rls_violations/clean_endpoint.py
@router.get("/secure")
@require_auth
async def secure_endpoint(request: Request, db: Session = Depends(obtener_db)):
    taller_id = request.state.taller_id
    tickets = db.query(Ticket).filter(Ticket.taller_id == taller_id).all()
    return tickets
```

**Test Cases:**
```python
def test_audit_detects_critical_violations():
    auditor = RLSAuditor()
    violations = auditor.scan_routes("tests/fixtures/rls_violations/critical_missing_filter.py")
    assert len(violations) == 1
    assert violations[0].severity == "CRITICAL"
    assert "taller_id filter" in violations[0].description

def test_audit_detects_high_violations():
    auditor = RLSAuditor()
    violations = auditor.scan_routes("tests/fixtures/rls_violations/high_missing_auth.py")
    assert len(violations) == 1
    assert violations[0].severity == "HIGH"
    assert "@require_auth" in violations[0].description

def test_audit_clean_file():
    auditor = RLSAuditor()
    violations = auditor.scan_routes("tests/fixtures/rls_violations/clean_endpoint.py")
    assert len(violations) == 0
```

## Implementation Plan

### Phase 1: Infrastructure (Requirements 6, 7)

1. Create `scripts/rls_audit.py` with RLSAuditor class
2. Create `tests/test_rls_audit.py` with audit script tests
3. Create `tests/test_rls_properties.py` with property-based tests
4. Run audit script to establish baseline of violations

### Phase 2: WhatsApp Routes (Requirement 1)

1. Add `@require_auth` to POST `/api/mobile/tickets/{id}/whatsapp` (C-03)
2. Add `@require_auth` to POST `/api/whatsapp/tickets/{id}/mensaje` (C-03)
3. Add `@require_auth` to GET `/api/mobile/whatsapp/logs` (C-04)
4. Add `taller_id` filter to GET `/api/mobile/whatsapp/logs` query (C-04)
5. Implement webhook routing logic in POST `/whatsapp/webhook` (C-05)
6. Add ticket ownership verification before WhatsApp operations (C-07)

### Phase 3: Economia Routes (Requirement 2)

1. Add `taller_id` parameter to `_base_query_dia()` helper (C-06)
2. Add `taller_id` parameter to `_sumar_por_tipo()` helper (C-06)
3. Update all economia endpoints to pass `request.state.taller_id` (C-06)
4. Add `@require_auth` to all economia endpoints (C-06)

### Phase 4: PDF Routes (Requirement 3)

1. Add `@require_auth` to all pdf_ruta.py endpoints (A-03)
2. Pass `taller_id=request.state.taller_id` when instantiating TicketRepository (C-09)
3. Add ticket ownership verification before PDF generation (C-09)

### Phase 5: Upload Routes (Requirement 4)

1. Add `@require_auth` to POST `/upload/foto` (A-01)
2. Add `@require_auth` to POST `/upload/compra` (A-01)
3. Add `@require_auth` to POST `/upload/firma` (A-01)
4. Add `taller_id` verification to file serving endpoints (A-02)
5. Add `@require_auth` to GET `/uploads/fotos/{filename}` (A-02)
6. Add `@require_auth` to GET `/uploads/compras/{filename}` (A-02)
7. Add `@require_auth` to GET `/uploads/firmas/{filename}` (A-02)

### Phase 6: Miscellaneous Routes (Requirement 5)

1. Add `@require_auth` to `cambiar_password_admin` in seguridad_ruta.py (M-01)
2. Add `@require_auth` to all ticket_ruta.py endpoints missing it (M-02)
3. Add `@require_auth` to `listar_mecanicos` in configuracion_ruta.py (M-03)

### Phase 7: Verification

1. Run audit script → should report 0 violations
2. Run property-based tests → should pass 100+ iterations
3. Run integration tests → should pass all scenarios
4. Manual security review of all modified files

## Security Considerations

### Defense in Depth

**Layer 1: Authentication**
- All endpoints require valid JWT token
- Tokens validated by AuthMiddleware
- Expired/invalid tokens rejected at middleware level

**Layer 2: Authorization**
- `taller_id` extracted from JWT (trusted source)
- Never accept `taller_id` from request body/query/headers
- SUPER_ADMIN users (taller_id=null) blocked from tenant endpoints

**Layer 3: Data Filtering**
- All queries filter by `taller_id`
- Cross-tenant access returns 404 (not 403)
- Repository layer enforces RLS automatically

**Layer 4: Audit & Monitoring**
- Automated audit script in CI/CD pipeline
- Property-based tests verify isolation
- Failed cross-tenant access attempts logged

### Attack Scenarios & Mitigations

**Attack 1: JWT Token Reuse Across Tenants**
- **Scenario:** Attacker obtains valid JWT for taller_id=1, attempts to access taller_id=2 data
- **Mitigation:** All queries filter by `request.state.taller_id` from JWT, not from request parameters
- **Result:** Attacker receives 404 for all taller_id=2 resources

**Attack 2: Parameter Tampering**
- **Scenario:** Attacker sends `{"taller_id": 2}` in request body while authenticated as taller_id=1
- **Mitigation:** Application ignores `taller_id` from request body, uses only `request.state.taller_id`
- **Result:** Resource created with taller_id=1 (from JWT), not taller_id=2 (from body)

**Attack 3: Webhook Spoofing**
- **Scenario:** Attacker sends fake WhatsApp webhook to inject messages into another tenant
- **Mitigation:** Webhook routing uses `To` field (WhatsApp Business phone number) to determine tenant
- **Result:** Message routed to correct tenant based on registered phone number, or rejected if unregistered

**Attack 4: File Path Traversal**
- **Scenario:** Attacker requests `/uploads/fotos/../../taller_2/foto.jpg` to access another tenant's files
- **Mitigation:** File serving endpoints validate `taller_id` from file path matches `request.state.taller_id`
- **Result:** Cross-tenant file access returns 404

**Attack 5: Audit Script Bypass**
- **Scenario:** Developer adds new endpoint without RLS, bypassing audit script
- **Mitigation:** Audit script runs in CI/CD pipeline, blocks merge if violations found
- **Result:** Pull request fails CI checks, cannot be merged

## Performance Considerations

### Query Optimization

**Before (N+1 Query Problem):**
```python
tickets = db.query(Ticket).all()
for ticket in tickets:
    logs = db.query(LogNotificacion).filter(LogNotificacion.ticket_id == ticket.id).all()
```

**After (Single Query with Join):**
```python
tickets = db.query(Ticket).filter(Ticket.taller_id == taller_id).all()
logs = db.query(LogNotificacion).filter(
    LogNotificacion.ticket_id.in_([t.id for t in tickets])
).all()
```

### Caching Strategy

**Webhook Routing Cache:**
```python
# Cache phone_number → taller_id mapping for 5 minutes
@lru_cache(maxsize=1000)
def get_taller_by_phone(phone_number: str) -> int | None:
    return db.query(Taller.id).filter(Taller.whatsapp_phone_number == phone_number).scalar()
```

**Audit Script Performance:**
- Target: Scan all route files in <10 seconds
- Strategy: Use AST parsing instead of regex for accuracy
- Optimization: Parallel file processing with multiprocessing

### Database Indexes

**Required Indexes (Assumed to Exist):**
- `tickets.taller_id` (for filtering)
- `movimientos_caja.taller_id` (for filtering)
- `log_notificacion.taller_id` (for filtering)
- `talleres.whatsapp_phone_number` (for webhook routing)

**Note:** Since models don't have `taller_id` columns, these indexes cannot be created. This is a known limitation.

## Deployment Considerations

### Rollout Strategy

**Phase 1: Audit & Baseline**
1. Deploy audit script to CI/CD pipeline
2. Run audit script against current codebase
3. Document all existing violations as baseline

**Phase 2: Fix Critical Violations**
1. Deploy fixes for C-03, C-04, C-05, C-06, C-07, C-09
2. Run audit script → verify critical violations resolved
3. Monitor logs for 404 errors (may indicate legitimate cross-tenant access attempts)

**Phase 3: Fix High/Medium Violations**
1. Deploy fixes for A-01, A-02, A-03, M-01, M-02, M-03
2. Run audit script → verify all violations resolved
3. Enable property-based tests in CI/CD pipeline

**Phase 4: Continuous Monitoring**
1. Audit script runs on every pull request
2. Property-based tests run on every merge to main
3. Failed cross-tenant access attempts logged and alerted

### Backward Compatibility

**Legacy Authentication:**
- Some endpoints currently accept `X-Admin-Password` header
- These will continue to work alongside JWT authentication
- Gradual migration: JWT preferred, `X-Admin-Password` deprecated

**API Contracts:**
- No breaking changes to request/response schemas
- Cross-tenant access that previously returned data will now return 404
- This is a security fix, not a breaking change

### Monitoring & Alerting

**Metrics to Track:**
- Count of 404 errors per endpoint (may indicate cross-tenant access attempts)
- Count of 401 errors per endpoint (may indicate missing authentication)
- Webhook routing failures (unregistered phone numbers)
- Audit script violations in CI/CD pipeline

**Alerts:**
- Spike in 404 errors on specific endpoint → investigate for attack
- Audit script finds new violations → block deployment
- Webhook routing failure rate >5% → investigate phone number registration

## Conclusion

This design provides a comprehensive solution to the 12 RLS violations identified in the security audit. By adding authentication decorators, implementing tenant-aware filtering, creating webhook routing logic, and establishing automated audit mechanisms, we ensure that:

1. All endpoints require authentication
2. All multi-tenant data is filtered by `taller_id` from JWT
3. Cross-tenant access attempts return 404 (not 403)
4. Webhook messages are routed to the correct tenant
5. Future RLS violations are detected before deployment
6. Tenant isolation is verified with property-based tests

The implementation follows the existing architectural patterns (AuthMiddleware, TenantRepository) and maintains backward compatibility with legacy authentication mechanisms while establishing a secure foundation for multi-tenant data access.
