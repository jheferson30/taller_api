# Resumen de Auditoría — Fase 1 (Tarea 2)

**Fecha:** 2026-04-25  
**Alcance:** Backend — `app/`  
**Herramientas:** vulture 2.16, radon 6.0.1, bandit 1.9.4, autoflake, análisis manual

---

## Resumen Ejecutivo

| Categoría | Hallazgos | Críticos | Altos | Medios | Bajos |
|-----------|-----------|----------|-------|--------|-------|
| Código muerto (vulture) | 4 | 0 | 0 | 0 | 4 |
| Complejidad ciclomática (radon) | 10 funciones CC>10 | 2 (CC>40) | 4 (CC>20) | 4 (CC>10) | — |
| Seguridad general (bandit) | 37 | 0 | 0 | 2 | 35 |
| Imports no usados (autoflake) | 3 | 0 | 0 | 0 | 3 |
| Auth faltante (2.5) | 14 endpoints | 5 | 9 | — | — |
| Queries sin taller_id (2.6) | 8 | 7 | 1 | 0 | 0 |
| taller_id del cliente (2.7) | 2 | 2 | 0 | 0 | 0 |
| Role mixing (2.8) | 0 | 0 | 0 | 0 | 0 |

**Total hallazgos de seguridad críticos: 14**

---

## 2.1 — Vulture: Código Muerto

**Reporte completo:** `vulture-report.txt`

**Hallazgos:** 4 variables `cls` no usadas en validadores Pydantic.

| Archivo | Línea | Hallazgo | Evaluación |
|---------|-------|----------|------------|
| `app/esquemas/auth_schema.py` | 100 | `cls` no usado | Falso positivo — requerido por @validator |
| `app/esquemas/auth_schema.py` | 120 | `cls` no usado | Falso positivo — requerido por @validator |
| `app/esquemas/user_schema.py` | 26 | `cls` no usado | Falso positivo — requerido por @validator |
| `app/esquemas/whatsapp_schema.py` | 17 | `cls` no usado | Falso positivo — requerido por @validator |

**Conclusión:** Todos son falsos positivos. El parámetro `cls` es requerido por la firma del decorador `@validator` de Pydantic aunque no se use en el cuerpo del método. No se requiere acción.

---

## 2.2 — Radon: Complejidad Ciclomática

**Reporte completo:** `radon-report.txt`

**Complejidad promedio del proyecto:** A (2.88) — Excelente

### Funciones con complejidad crítica (CC > 20 — candidatas urgentes a refactorización):

| Función | Archivo | CC | Grado |
|---------|---------|-----|-------|
| `generar_pdf_ticket_completo` | `app/utils/pdf_generator.py:114` | 77 | F |
| `generar_pdf_economia_profesional` | `app/utils/pdf_economia.py:70` | 49 | F |
| `sincronizar_operaciones_batch` | `app/rutas/mobile_api_ruta.py:713` | 29 | D |
| `AuthMiddleware.dispatch` | `app/seguridad/auth_middleware.py:52` | 28 | D |
| `generar_pdf_cliente` | `app/rutas/ticket_ruta.py:926` | 26 | D |
| `validate_config` | `app/configuracion/config_validator.py:18` | 26 | D |

### Funciones con complejidad alta (CC 11-20):

| Función | Archivo | CC |
|---------|---------|-----|
| `AuthMiddleware` (clase) | `app/seguridad/auth_middleware.py:24` | 16 |
| `get_tickets_with_details` | `app/repositorios/ticket_repository.py:57` | 16 |
| `economia_hoy_mobile` | `app/rutas/mobile_api_ruta.py:981` | 15 |
| `generar_ticket_desde_cita` | `app/servicios/cita_service.py:105` | 15 |
| `entregar_ticket` | `app/servicios/ticket_service.py:143` | 14 |
| `cambiar_password_admin` | `app/rutas/seguridad_ruta.py:161` | 13 |
| `enviar_notificacion` | `app/servicios/twilio_whatsapp_service.py:14` | 11 |
| `enviar_mensaje_manual` | `app/servicios/twilio_whatsapp_service.py:126` | 11 |
| `crear_o_actualizar_vehiculo` | `app/servicios/cita_service.py:23` | 11 |
| `buscar_tickets` | `app/rutas/ticket_ruta.py:198` | 11 |

**Prioridad de refactorización:** Las dos funciones de generación de PDF (CC=77 y CC=49) son las más urgentes.

---

## 2.3 — Bandit: Seguridad General

**Reporte completo:** `bandit-report.txt`

**Total líneas analizadas:** 14,244  
**Issues High:** 0 ✅  
**Issues Medium:** 2  
**Issues Low:** 35 (33 son falsos positivos)

### Hallazgos reales (no falsos positivos):

| Severidad | Archivo | Línea | Descripción |
|-----------|---------|-------|-------------|
| MEDIO | `app/main.py` | 720 | `urllib.request.urlopen` a api.ipify.org — usar httpx |
| MEDIO | `app/rutas/health.py` | 25 | Misma función duplicada — consolidar en helper |
| BAJO | `app/utils/pdf_economia.py` | 159 | `except Exception: pass` sin logging |
| BAJO | `app/utils/pdf_generator.py` | 213, 353 | `except Exception: pass` sin logging |

### Falsos positivos (35 hallazgos — no requieren acción):
- Contraseñas en `json_schema_extra` (ejemplos de documentación OpenAPI)
- Valores de enum `AuditAction` con "PASSWORD" en el nombre
- Valores de campo `token_type` ("access", "refresh")
- Booleanos `False` en diccionarios de resultados

---

## 2.4 — Imports No Usados

**Reporte completo:** `unused-imports-report.txt`

**Resultado autoflake:** 0 imports no usados detectados ✅

### Hallazgos menores (imports lazy dentro de funciones):

| Archivo | Línea | Import | Severidad |
|---------|-------|--------|-----------|
| `app/rutas/whatsapp_ruta.py` | ~47 | `from app.modelos.configuracion_taller import ConfiguracionTaller` | BAJO |
| `app/rutas/seguridad_ruta.py` | ~185 | `import hmac as _hmac` | BAJO |
| `app/rutas/citas_ruta.py` | ~65 | `from app.servicios.cita_service import CitaService` | BAJO |

**Conclusión:** El código tiene una gestión de imports muy limpia. Los imports lazy son un antipatrón menor que no afecta funcionalidad.

---

## 2.5 — Seguridad: Endpoints sin @require_auth

**Reporte completo:** `security-auth-report.txt`

### 🔴 CRÍTICO — Endpoints completamente desprotegidos:

| Archivo | Endpoint | Problema |
|---------|----------|---------|
| `app/rutas/mobile_ruta.py` | `GET /mobile/v1/tickets/activos` | Sin auth + sin filtro taller_id |
| `app/rutas/mobile_ruta.py` | `GET /mobile/v1/tickets/{id}/timeline` | Sin auth + sin filtro taller_id |
| `app/rutas/whatsapp_ruta.py` | `POST /api/mobile/tickets/{id}/whatsapp` | Sin auth |
| `app/rutas/whatsapp_ruta.py` | `POST /api/whatsapp/tickets/{id}/mensaje` | Sin auth |
| `app/rutas/whatsapp_ruta.py` | `GET /api/mobile/whatsapp/logs` | Sin auth + sin filtro taller_id |

### 🟠 ALTO — Endpoints sin @require_auth explícito:

| Archivo | Endpoints | Problema |
|---------|-----------|---------|
| `app/rutas/upload_ruta.py` | POST /foto, /compra, /firma | Sin @require_auth decorador |
| `app/rutas/upload_ruta.py` | GET /fotos/{taller_id}/{filename} | Archivos accesibles sin auth |
| `app/rutas/pdf_ruta.py` | POST /generate, GET /status, GET /download | Sin auth |

### 🟡 MEDIO — Antipatrones de auth:

| Archivo | Endpoints | Problema |
|---------|-----------|---------|
| `app/rutas/seguridad_ruta.py` | POST /admin/cambiar-password | Verifica rol manualmente sin @require_auth |
| `app/rutas/ticket_ruta.py` | Múltiples endpoints | Usan request.state sin @require_auth explícito |
| `app/rutas/configuracion_ruta.py` | GET /mecanicos | Sin @require_auth explícito |

---

## 2.6 — Seguridad: Queries sin filtro taller_id

**Reporte completo:** `security-tenant-queries-report.txt`

### 🔴 CRÍTICO — Violaciones de aislamiento multi-tenant:

| Archivo | Función | Tabla | Problema |
|---------|---------|-------|---------|
| `app/rutas/mobile_ruta.py` | `tickets_activos_mobile` | Ticket | Sin filtro taller_id — devuelve todos los talleres |
| `app/rutas/mobile_ruta.py` | `timeline_ticket_mobile` | TicketProceso, TicketFoto | Sin verificación de pertenencia al taller |
| `app/rutas/whatsapp_ruta.py` | `recibir_webhook` | ConfiguracionTaller | Obtiene primer taller con WhatsApp — no filtra |
| `app/rutas/whatsapp_ruta.py` | `enviar_whatsapp_mobile/web` | Ticket, Vehiculo | Sin verificación de pertenencia al taller |
| `app/rutas/whatsapp_ruta.py` | `obtener_logs` | LogNotificacion | Sin filtro taller_id — devuelve todos los talleres |
| `app/rutas/economia_ruta.py` | Múltiples helpers | MovimientoCaja | Sin filtro taller_id — devuelve todos los talleres |

### 🟠 ALTO:

| Archivo | Función | Problema |
|---------|---------|---------|
| `app/rutas/pdf_ruta.py` | `generate_ticket_pdf` | TicketRepository instanciado sin taller_id |

### ✅ Bien implementados:
Todos los repositorios que heredan `TenantRepository` aplican el filtro automáticamente. Las rutas de tickets, vehículos, citas, usuarios, movimientos de caja y configuración usan correctamente `request.state.taller_id`.

---

## 2.7 — Seguridad: taller_id del cliente vs JWT

**Reporte completo:** `security-taller-id-report.txt`

**Patrones incorrectos (datos.taller_id, body.taller_id, query_params):** 0 ✅

### 🔴 CRÍTICO — Uso de taller_id de BD sin verificación contra JWT:

| Archivo | Función | Línea | Descripción |
|---------|---------|-------|-------------|
| `app/rutas/whatsapp_ruta.py` | `enviar_whatsapp_mobile` | ~80 | Usa `ticket.taller_id` sin verificar contra JWT |
| `app/rutas/whatsapp_ruta.py` | `enviar_whatsapp_web` | ~100 | Usa `ticket.taller_id` sin verificar contra JWT |

**Conclusión:** No se encontraron casos donde el taller_id venga directamente del body o query params del cliente. Los archivos que usan `request.state.taller_id` lo hacen correctamente.

---

## 2.8 — Seguridad: Role Mixing SUPER_ADMIN

**Reporte completo:** `security-role-mixing-report.txt`

**Mezclas SUPER_ADMIN + roles de taller:** 0 ✅

**Conclusión:** No se encontraron violaciones. El SUPER_ADMIN nunca está mezclado con roles de taller. Los endpoints de notificación mezclan ADMIN+MECANICO (correcto y documentado).

---

## Hallazgos Críticos Consolidados

Los siguientes problemas requieren atención inmediata antes de cualquier limpieza de código:

### 🔴 CRÍTICO — Violaciones de seguridad multi-tenant:

1. **`app/rutas/mobile_ruta.py`** — Dos endpoints sin autenticación que exponen datos de todos los talleres sin filtro taller_id. Cualquier persona con acceso a la red puede ver todos los tickets activos y timelines.

2. **`app/rutas/whatsapp_ruta.py`** — Tres endpoints sin autenticación que permiten enviar mensajes de WhatsApp y consultar logs de todos los talleres sin restricción.

3. **`app/rutas/economia_ruta.py`** — Las funciones helper de economía no filtran por taller_id, mezclando datos financieros de todos los talleres.

4. **`app/rutas/pdf_ruta.py`** — TicketRepository instanciado sin taller_id, violando el contrato de TenantRepository.

### 🟠 ALTO — Problemas de autenticación:

5. **`app/rutas/upload_ruta.py`** — Endpoints de subida de archivos sin @require_auth explícito. Los archivos son accesibles públicamente si se conoce el taller_id y nombre de archivo.

### 🟡 MEDIO — Complejidad excesiva (candidatos a refactorización):

6. **`app/utils/pdf_generator.py:114`** — `generar_pdf_ticket_completo` con CC=77 (grado F)
7. **`app/utils/pdf_economia.py:70`** — `generar_pdf_economia_profesional` con CC=49 (grado F)

---

## Archivos de Reporte Generados

| Archivo | Tarea | Estado |
|---------|-------|--------|
| `vulture-report.txt` | 2.1 | ✅ Completado |
| `radon-report.txt` | 2.2 | ✅ Completado |
| `bandit-report.txt` | 2.3 | ✅ Completado |
| `unused-imports-report.txt` | 2.4 | ✅ Completado |
| `security-auth-report.txt` | 2.5 | ✅ Completado |
| `security-tenant-queries-report.txt` | 2.6 | ✅ Completado |
| `security-taller-id-report.txt` | 2.7 | ✅ Completado |
| `security-role-mixing-report.txt` | 2.8 | ✅ Completado |
| `audit-summary-2.md` | Resumen | ✅ Completado |
