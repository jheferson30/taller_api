---
inclusion: auto
priority: 1
---

# 🔒 Estándares de Seguridad Obligatorios — TODO CÓDIGO NUEVO

**CRÍTICO:** Este documento define los estándares de seguridad que **DEBEN** aplicarse a **TODO** código nuevo que se escriba en este proyecto, sin excepción.

**Aplicación:** Automática para todos los endpoints, servicios, y funcionalidades nuevas.

---

## 🎯 Regla de Oro

> **TODO endpoint nuevo, servicio nuevo, o funcionalidad nueva DEBE cumplir con TODOS los estándares de seguridad implementados en los specs: seguridad-secretos, seguridad-csrf, y seguridad-rls.**

---

## ✅ Checklist Obligatorio para TODO Código Nuevo

### 1. Autenticación y Autorización (seguridad-rls)

#### Para TODOS los endpoints (excepto públicos explícitos):

```python
# ✅ CORRECTO — Siempre usar @require_auth
@router.post("/api/nuevo-endpoint")
@require_auth
@limiter.limit("30/minute")
async def nuevo_endpoint(
    request: Request,
    datos: NuevoSchema,
    db: Session = Depends(obtener_db)
):
    # Extraer taller_id del JWT (NUNCA del body/params)
    taller_id = request.state.taller_id
    
    # Validar que no sea SUPER_ADMIN si es endpoint de taller
    if taller_id is None:
        raise HTTPException(
            status_code=403,
            detail="SUPER_ADMIN cannot access tenant endpoints"
        )
    
    # Filtrar por taller_id en TODAS las queries
    query = db.query(Model).filter(Model.taller_id == taller_id)
    
    # ...resto del código
```

#### Endpoints públicos (excepciones):
- `/auth/login`
- `/auth/refresh`
- `/auth/forgot-password`
- `/auth/reset-password`
- `/health`
- `/info`
- `/docs`
- `/openapi.json`
- `/whatsapp/webhook` (webhook externo)

**Todos los demás endpoints DEBEN tener `@require_auth`**

---

### 2. Row-Level Security (RLS) — Aislamiento Multi-Tenant

#### Regla Fundamental:
```python
# ❌ NUNCA hacer esto
taller_id = datos.taller_id  # Del body
taller_id = request.query_params.get("taller_id")  # De query params
taller_id = request.headers.get("X-Taller-ID")  # De headers

# ✅ SIEMPRE hacer esto
taller_id = request.state.taller_id  # Del JWT validado
```

#### Para TODAS las queries en tablas multi-tenant:

```python
# ✅ CORRECTO — Siempre filtrar por taller_id
tickets = db.query(Ticket).filter(
    Ticket.taller_id == request.state.taller_id
).all()

# ✅ CORRECTO — Verificar ownership antes de retornar
ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
if not ticket:
    raise HTTPException(status_code=404, detail="Resource not found")

if ticket.taller_id != request.state.taller_id:
    # Retornar 404 (no 403) para no revelar que existe
    raise HTTPException(status_code=404, detail="Resource not found")

return ticket
```

#### Tablas Multi-Tenant (SIEMPRE filtrar por taller_id):
- `Ticket`
- `MovimientoCaja`
- `LogNotificacion`
- `Vehiculo`
- `Cliente`
- `Mecanico`
- `TicketProceso`
- `TicketRepuesto`
- `TicketFoto`
- `TicketCompra`
- `TicketCobro`

---

### 3. Protección CSRF (seguridad-csrf)

#### Para TODOS los endpoints de escritura:

```python
# ✅ CORRECTO — Métodos de escritura automáticamente protegidos
@router.post("/api/nuevo-recurso")
@require_auth
async def crear_recurso(request: Request, datos: Schema):
    # CSRF middleware valida automáticamente el token
    # en header X-CSRF-Token para POST/PUT/PATCH/DELETE
    pass
```

#### Frontend DEBE incluir token CSRF:

```javascript
// ✅ CORRECTO — Siempre incluir X-CSRF-Token
const response = await api.post('/api/nuevo-recurso', datos, {
    headers: {
        'X-CSRF-Token': getCsrfToken()  // Del cookie
    }
});
```

#### Endpoints exentos de CSRF (solo estos):
- `/auth/login`
- `/auth/refresh`
- `/auth/forgot-password`
- `/auth/reset-password`
- `/whatsapp/webhook`

**Todos los demás POST/PUT/PATCH/DELETE requieren token CSRF**

---

### 4. Gestión de Secretos (seguridad-secretos)

#### NUNCA hardcodear secretos:

```python
# ❌ NUNCA hacer esto
JWT_SECRET = "mi-clave-secreta-123"
DB_PASSWORD = "postgres123"
API_KEY = "abc123xyz"

# ✅ SIEMPRE hacer esto
from app.configuracion.secrets_manager import SecretsManager

secrets_manager = SecretsManager()
jwt_secret = secrets_manager.get_secret(
    "jwt-secret-key",
    fallback_env_var="JWT_SECRET_KEY"
)
```

#### Para datos sensibles (PII):

```python
# ✅ CORRECTO — Usar EncryptedString para PII
from app.utils.pii_encryptor import EncryptedString

class Cliente(Base):
    __tablename__ = "clientes"
    
    id = Column(Integer, primary_key=True)
    nombre = Column(String(100))  # No sensible
    
    # Datos sensibles — SIEMPRE encriptar
    telefono = Column(EncryptedString(20))
    email = Column(EncryptedString(100))
    direccion = Column(EncryptedString(200))
    documento_identidad = Column(EncryptedString(50))
```

---

### 5. Rate Limiting

#### Para TODOS los endpoints:

```python
# ✅ CORRECTO — Siempre agregar rate limiting
@router.post("/api/nuevo-endpoint")
@require_auth
@limiter.limit("30/minute")  # Ajustar según criticidad
async def nuevo_endpoint(request: Request):
    pass
```

#### Límites recomendados por tipo de endpoint:

| Tipo de Endpoint | Límite Recomendado |
|------------------|-------------------|
| Autenticación (login, reset) | 5/minute |
| Escritura (POST/PUT/PATCH) | 30/minute |
| Lectura (GET) | 100/minute |
| Upload de archivos | 10/minute |
| Webhooks externos | 5/minute |
| Operaciones críticas | 10/minute |

---

### 6. Validación y Sanitización de Entrada

#### Para TODOS los inputs de usuario:

```python
from app.utils.input_validator import InputSanitizer

# ✅ CORRECTO — Siempre validar y sanitizar
@router.post("/api/nuevo-recurso")
@require_auth
async def crear_recurso(
    request: Request,
    datos: RecursoCrear,
    db: Session = Depends(obtener_db)
):
    # Sanitizar HTML/texto
    descripcion_limpia = InputSanitizer.sanitize_html(datos.descripcion)
    
    # Validar formato de email
    if datos.email:
        InputSanitizer.validate_email(datos.email)
    
    # Validar formato de teléfono
    if datos.telefono:
        InputSanitizer.validate_phone(datos.telefono)
    
    # Crear recurso con datos sanitizados
    recurso = Recurso(
        descripcion=descripcion_limpia,
        taller_id=request.state.taller_id
    )
    db.add(recurso)
    db.commit()
```

---

### 7. Audit Log

#### Para TODAS las acciones críticas:

```python
from app.modelos.audit_log import AuditLog, AuditAction

# ✅ CORRECTO — Registrar acciones críticas
@router.post("/api/recurso-critico")
@require_auth
async def accion_critica(
    request: Request,
    datos: Schema,
    db: Session = Depends(obtener_db)
):
    taller_id = request.state.taller_id
    user = request.state.user
    
    # Realizar acción
    recurso = crear_recurso(datos, taller_id)
    
    # Registrar en audit log
    audit_entry = AuditLog(
        user_id=user.id,
        taller_id=taller_id,
        action=AuditAction.RECURSO_CREADO,  # Usar enum tipado
        resource_type="Recurso",
        resource_id=recurso.id,
        details={"nombre": recurso.nombre},
        ip_address=request.client.host
    )
    db.add(audit_entry)
    db.commit()
    
    return recurso
```

#### Acciones que DEBEN registrarse:
- Login/Logout
- Cambio de contraseña
- Creación/eliminación de recursos críticos
- Acceso a datos sensibles (PII)
- Intentos de acceso cross-tenant
- Errores de autenticación
- Acciones de SUPER_ADMIN

---

### 8. Manejo de Errores Seguro

#### NUNCA exponer detalles internos:

```python
# ❌ NUNCA hacer esto
except Exception as e:
    raise HTTPException(
        status_code=500,
        detail=f"Error en base de datos: {str(e)}"  # Expone detalles
    )

# ✅ SIEMPRE hacer esto
except Exception as e:
    # Loguear detalles internamente
    logger.error(f"Error en crear_recurso: {str(e)}", exc_info=True)
    
    # Retornar mensaje genérico al cliente
    raise HTTPException(
        status_code=500,
        detail="Internal server error"
    )
```

#### Para acceso cross-tenant:

```python
# ✅ CORRECTO — Retornar 404 (no 403)
if recurso.taller_id != request.state.taller_id:
    # No revelar que el recurso existe en otro taller
    raise HTTPException(
        status_code=404,
        detail="Resource not found"
    )
```

---

### 9. Headers de Seguridad HTTP

Los headers de seguridad se agregan automáticamente por el middleware, pero verifica que estén presentes:

```python
# Automático — No requiere código adicional
# Security Headers Middleware agrega:
# - X-Content-Type-Options: nosniff
# - X-Frame-Options: DENY
# - X-XSS-Protection: 1; mode=block
# - Referrer-Policy: strict-origin-when-cross-origin
# - Content-Security-Policy: default-src 'self'
# - Strict-Transport-Security (solo en producción)
```

---

### 10. CORS Estricto

#### En producción, SIEMPRE configurar orígenes específicos:

```python
# ❌ NUNCA en producción
ALLOWED_ORIGINS=*

# ✅ SIEMPRE en producción
ALLOWED_ORIGINS=https://taller.com,https://app.taller.com
ALLOWED_HOSTS=taller.com,*.taller.com
```

---

## 📋 Template de Endpoint Nuevo (COPIAR Y USAR)

```python
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.configuracion.base_datos import obtener_db
from app.configuracion.limiter import limiter
from app.modelos.audit_log import AuditAction, AuditLog
from app.seguridad.auth_middleware import require_auth
from app.utils.input_validator import InputSanitizer

router = APIRouter(prefix="/api/nuevo-modulo", tags=["Nuevo Módulo"])


@router.post("/recursos")
@require_auth
@limiter.limit("30/minute")
async def crear_recurso(
    request: Request,
    datos: RecursoCrear,
    db: Session = Depends(obtener_db)
):
    """
    Crea un nuevo recurso.
    
    Seguridad:
    - Requiere autenticación JWT (@require_auth)
    - Protección CSRF automática (POST)
    - Rate limiting: 30 requests/minuto
    - RLS: Filtra por taller_id del JWT
    - Audit log: Registra creación
    """
    # 1. Extraer taller_id del JWT (NUNCA del body)
    taller_id = request.state.taller_id
    user = request.state.user
    
    # 2. Validar que no sea SUPER_ADMIN (si aplica)
    if taller_id is None:
        raise HTTPException(
            status_code=403,
            detail="SUPER_ADMIN cannot access tenant endpoints"
        )
    
    # 3. Sanitizar inputs
    nombre_limpio = InputSanitizer.sanitize_html(datos.nombre)
    
    # 4. Crear recurso con taller_id del JWT
    recurso = Recurso(
        nombre=nombre_limpio,
        taller_id=taller_id,  # Del JWT, no del body
        created_by=user.id
    )
    db.add(recurso)
    db.flush()  # Para obtener el ID
    
    # 5. Registrar en audit log
    audit_entry = AuditLog(
        user_id=user.id,
        taller_id=taller_id,
        action=AuditAction.RECURSO_CREADO,
        resource_type="Recurso",
        resource_id=recurso.id,
        details={"nombre": recurso.nombre},
        ip_address=request.client.host
    )
    db.add(audit_entry)
    
    # 6. Commit
    db.commit()
    db.refresh(recurso)
    
    return recurso


@router.get("/recursos/{recurso_id}")
@require_auth
@limiter.limit("100/minute")
async def obtener_recurso(
    request: Request,
    recurso_id: int,
    db: Session = Depends(obtener_db)
):
    """
    Obtiene un recurso por ID.
    
    Seguridad:
    - Requiere autenticación JWT
    - RLS: Verifica ownership por taller_id
    - Retorna 404 si no pertenece al taller (no 403)
    """
    taller_id = request.state.taller_id
    
    # Buscar recurso
    recurso = db.query(Recurso).filter(Recurso.id == recurso_id).first()
    
    if not recurso:
        raise HTTPException(status_code=404, detail="Resource not found")
    
    # Verificar ownership (RLS)
    if recurso.taller_id != taller_id:
        # Retornar 404 (no 403) para no revelar existencia
        raise HTTPException(status_code=404, detail="Resource not found")
    
    return recurso


@router.get("/recursos")
@require_auth
@limiter.limit("100/minute")
async def listar_recursos(
    request: Request,
    db: Session = Depends(obtener_db)
):
    """
    Lista todos los recursos del taller.
    
    Seguridad:
    - Requiere autenticación JWT
    - RLS: Filtra automáticamente por taller_id
    """
    taller_id = request.state.taller_id
    
    # Filtrar por taller_id (RLS)
    recursos = db.query(Recurso).filter(
        Recurso.taller_id == taller_id
    ).all()
    
    return recursos
```

---

## 🚨 Validación Automática

### Script de Auditoría RLS

Ejecutar ANTES de cada commit:

```bash
# Verificar que no hay violaciones de seguridad
python scripts/rls_audit.py

# Debe retornar: 0 violations found
```

### Tests Obligatorios

Para CADA endpoint nuevo, crear tests que verifiquen:

```python
def test_nuevo_endpoint_sin_jwt_retorna_401(client):
    """Verifica que endpoint requiere autenticación."""
    response = client.post("/api/nuevo-endpoint", json={})
    assert response.status_code == 401


def test_nuevo_endpoint_cross_tenant_retorna_404(client, db):
    """Verifica aislamiento multi-tenant."""
    # Crear recurso en taller_id=1
    recurso = crear_recurso(db, taller_id=1)
    
    # Intentar acceder con JWT de taller_id=2
    jwt_token = generate_jwt(taller_id=2)
    response = client.get(
        f"/api/recursos/{recurso.id}",
        headers={"Authorization": f"Bearer {jwt_token}"}
    )
    
    # Debe retornar 404 (no 403)
    assert response.status_code == 404


def test_nuevo_endpoint_sin_csrf_retorna_403(client):
    """Verifica protección CSRF."""
    jwt_token = generate_jwt(taller_id=1)
    response = client.post(
        "/api/nuevo-endpoint",
        json={},
        headers={"Authorization": f"Bearer {jwt_token}"}
        # Sin X-CSRF-Token
    )
    assert response.status_code == 403
```

---

## ✅ Checklist Final para Código Nuevo

Antes de considerar completo cualquier endpoint/funcionalidad nueva:

- [ ] Tiene `@require_auth` (excepto endpoints públicos explícitos)
- [ ] Tiene `@limiter.limit()` con límite apropiado
- [ ] Extrae `taller_id` de `request.state.taller_id` (no del body/params)
- [ ] Filtra TODAS las queries por `taller_id`
- [ ] Verifica ownership antes de retornar recursos
- [ ] Retorna 404 (no 403) para acceso cross-tenant
- [ ] Sanitiza todos los inputs de usuario
- [ ] Registra acciones críticas en audit log
- [ ] Maneja errores sin exponer detalles internos
- [ ] Usa `EncryptedString` para datos PII
- [ ] Tiene tests de autenticación (401 sin JWT)
- [ ] Tiene tests de RLS (404 cross-tenant)
- [ ] Tiene tests de CSRF (403 sin token)
- [ ] Pasa el script de auditoría RLS

---

## 🔍 Revisión de Código

Antes de aprobar cualquier PR, verificar:

1. **Autenticación:** ¿Todos los endpoints tienen `@require_auth`?
2. **RLS:** ¿Todas las queries filtran por `taller_id` del JWT?
3. **CSRF:** ¿Los endpoints de escritura están protegidos?
4. **Rate Limiting:** ¿Todos los endpoints tienen límites?
5. **Validación:** ¿Los inputs están sanitizados?
6. **Audit Log:** ¿Las acciones críticas se registran?
7. **Tests:** ¿Hay tests de seguridad?
8. **Secretos:** ¿No hay credenciales hardcodeadas?

---

**Este documento es OBLIGATORIO para todo código nuevo. No hay excepciones.**

**Última actualización:** 9 de Mayo, 2026  
**Versión:** 1.0  
**Estado:** ✅ ACTIVO Y OBLIGATORIO
