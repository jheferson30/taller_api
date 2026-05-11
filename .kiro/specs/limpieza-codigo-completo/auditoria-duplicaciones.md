# Auditoría de Duplicaciones — Fase 1

> Generado: Tarea 3 — Auditoría manual de duplicaciones conocidas
> Archivos analizados: mobile_ruta.py, mobile_api_ruta.py, whatsapp_service.py,
> twilio_whatsapp_service.py, pdf_generator.py, pdf_economia.py,
> tenant_repository.py, todos los archivos en app/servicios/ y app/rutas/

---

## 3.1 Rutas Mobile

### Cuál está registrado en main.py

**`app/rutas/mobile_api_ruta.py`** es el que está registrado en `main.py`.

Evidencia en `main.py`:
```python
from app.rutas import (
    ...
    mobile_api_ruta,
    ...
)
...
app.include_router(mobile_api_ruta.router)
```

`mobile_ruta.py` **no aparece en ningún import ni `include_router` de `main.py`**.

### Cuál es redundante

**`app/rutas/mobile_ruta.py`** es el archivo redundante — no está registrado en ningún router.

### Diferencias encontradas

| Característica | `mobile_ruta.py` | `mobile_api_ruta.py` |
|---|---|---|
| Prefijo de ruta | `/mobile/v1` | `/api/mobile` |
| Autenticación | Sin autenticación (endpoints públicos) | `requerir_password_admin` en todos los endpoints |
| Líneas de código | ~75 líneas | ~1034 líneas |
| Endpoints | 3 endpoints básicos | 20+ endpoints completos |
| Schemas Pydantic | No usa schemas | Usa `app/esquemas/mobile_schema.py` |
| Modo offline/sync | No | Sí — endpoint `/sync/batch` completo |
| Finanzas | No | Sí — cobros, compras, finanzas |
| WhatsApp | No | Sí — notificaciones en entrega |
| Estadísticas | No | Sí — `/estadisticas`, `/economia-hoy` |

**Endpoints únicos en `mobile_ruta.py` (no presentes en `mobile_api_ruta.py`):**
- `GET /mobile/v1/health` — health check específico de mobile v1
- `GET /mobile/v1/tickets/activos` — lista tickets activos con filtro por placa (sin auth)
- `GET /mobile/v1/tickets/{ticket_id}/timeline` — timeline de procesos y fotos (sin auth)

**Endpoints únicos en `mobile_api_ruta.py` (no presentes en `mobile_ruta.py`):**
- `POST /api/mobile/sync/batch` — sincronización offline por lotes
- `GET /api/mobile/economia-hoy` — resumen económico del día
- `GET /api/mobile/estadisticas` — estadísticas del dashboard
- `GET /api/mobile/mecanicos` — lista mecánicos activos
- `GET /api/mobile/procesos-rapidos` — procesos rápidos configurados
- `GET /api/mobile/cobros-rapidos` — cobros rápidos configurados
- Endpoints completos de cobros, compras, fotos, repuestos, procesos con foto

### Recomendación

**Eliminar `app/rutas/mobile_ruta.py`** — es un archivo obsoleto que nunca fue registrado en
`main.py`. Sus 3 endpoints son un subconjunto simplificado (y sin autenticación) de lo que ya
ofrece `mobile_api_ruta.py`. El endpoint `/mobile/v1/health` puede ignorarse ya que
`mobile_api_ruta.py` no lo necesita (el health general está en `health.py`).

**Riesgo:** Bajo — el archivo no está registrado, por lo que eliminarlo no afecta ninguna
funcionalidad activa.

**Advertencia de seguridad:** `mobile_ruta.py` expone tickets sin autenticación alguna
(`GET /mobile/v1/tickets/activos` y `GET /mobile/v1/tickets/{ticket_id}/timeline`). Aunque
no está registrado, su existencia es un riesgo si alguien lo registra accidentalmente.

---

## 3.2 Servicios WhatsApp

### Cuál provider está activo

**`app/servicios/twilio_whatsapp_service.py`** (`TwilioWhatsAppService`) es el provider activo.

Evidencia:
1. `mobile_api_ruta.py` importa y usa directamente `TwilioWhatsAppService`:
   ```python
   from app.servicios.twilio_whatsapp_service import TwilioWhatsAppService
   _whatsapp_service = TwilioWhatsAppService()
   ```
2. `app/rutas/whatsapp_ruta.py` también usa `TwilioWhatsAppService` (verificado por grep).
3. `app/servicios/whatsapp_service.py` es solo una **clase base abstracta** (`ABC`) — no es
   un servicio concreto, no puede instanciarse directamente.

### Diferencias entre ambos archivos

| Característica | `whatsapp_service.py` | `twilio_whatsapp_service.py` |
|---|---|---|
| Tipo | Clase abstracta (`ABC`) | Implementación concreta |
| Instanciable | No | Sí |
| Métodos | 2 métodos abstractos | Implementación completa + helpers |
| Proveedor | N/A (interfaz) | Twilio API |
| Logging | No | Sí — persiste en `log_notificacion` |
| Construcción de mensajes | No | Sí — `_construir_mensaje()` |
| Manejo de errores | No | Sí — captura excepciones HTTP |

**`whatsapp_service.py` define:**
- `TipoEvento` (StrEnum): RECEPCION, FINALIZACION, ENTREGA, MANUAL, ENTRANTE
- `ResultadoEnvio` (StrEnum): ENVIADO, ERROR, OMITIDO
- `WhatsAppService` (ABC): interfaz con `enviar_notificacion()` y `enviar_mensaje_manual()`

**`twilio_whatsapp_service.py` define:**
- `TwilioWhatsAppService(WhatsAppService)`: implementación concreta que hereda de la interfaz

### Recomendación

**Mantener ambos archivos** — la arquitectura actual es correcta y sigue el patrón Strategy:
- `whatsapp_service.py` es la interfaz/contrato (Strategy interface)
- `twilio_whatsapp_service.py` es la implementación concreta (Concrete Strategy)

Sin embargo, hay una **oportunidad de mejora**: los enums `TipoEvento` y `ResultadoEnvio`
están definidos en `whatsapp_service.py` pero `mobile_api_ruta.py` los importa desde ahí
mientras instancia `TwilioWhatsAppService`. Esto es correcto y no requiere cambios.

**Acción recomendada:** Ninguna eliminación. Documentar en el código que `whatsapp_service.py`
es la interfaz y que para agregar un nuevo provider (ej. Meta Cloud API) se debe crear una
nueva clase que herede de `WhatsAppService`.

---

## 3.3 Generadores de PDF

### ¿Tienen responsabilidades distintas?

**Sí — tienen responsabilidades completamente distintas:**

| Característica | `pdf_generator.py` | `pdf_economia.py` |
|---|---|---|
| Función principal | `generar_pdf_ticket_completo()` | `generar_pdf_economia_profesional()` |
| Propósito | Comprobante de servicio de un ticket | Reporte de economía diaria del taller |
| Inputs | ticket_data, procesos, repuestos, fotos, cobros, compras | fecha, resumen, ingresos, egresos |
| Contenido del PDF | Info del vehículo, procesos, repuestos, fotos, cobros, finanzas del ticket | Tarjetas de resumen, anticipos, cobros finales, cobros rápidos, egresos por categoría |
| Función wrapper | `generar_pdf_ticket()` — wrapper que consulta la BD | No tiene wrapper |
| Líneas de código | ~886 líneas | ~500 líneas |

### ¿Hay funciones duplicadas?

**Sí — hay duplicación real de código auxiliar:**

1. **`imagen_escalada()`** — función idéntica en ambos archivos (misma lógica, mismo nombre):
   - `pdf_generator.py` líneas ~75-95
   - `pdf_economia.py` líneas ~18-32
   - Diferencia menor: `pdf_generator.py` tiene un comentario adicional

2. **`fmt_cop()`** — función idéntica en ambos archivos:
   - `pdf_generator.py`: `def fmt_cop(valor) -> str:`
   - `pdf_economia.py`: `def fmt_cop(valor) -> str:`
   - Implementación 100% idéntica

3. **Paleta de colores** — constantes duplicadas (AZUL, AZUL_MEDIO, AZUL_CLARO, GRIS_BORDE,
   GRIS_FILA, TEXTO, TEXTO_MUTED):
   - `pdf_economia.py` incluso tiene un comentario `# ── Paleta (misma que pdf_generator.py)`
   - `pdf_economia.py` agrega colores adicionales: VERDE_MEDIO, ROJO, ROJO_MEDIO, ROJO_BG

4. **Lógica del encabezado con logo** — el bloque de código para resolver la ruta del logo
   y construir el encabezado del PDF es casi idéntico en ambos archivos (~30 líneas duplicadas).

5. **Estilos de párrafo** — la función `estilo()` local y los estilos base son similares
   aunque con nombres distintos.

### Recomendación

**Extraer utilidades comunes a `app/utils/pdf_utils.py`** con:
- `imagen_escalada()` — función compartida
- `fmt_cop()` — función compartida
- Paleta de colores base (AZUL, AZUL_MEDIO, etc.)
- `construir_encabezado_taller()` — helper para el encabezado con logo

Luego hacer que `pdf_generator.py` y `pdf_economia.py` importen desde `pdf_utils.py`.

**No consolidar en un solo archivo** — las responsabilidades son distintas y mezclarlas
haría el código más difícil de mantener.

**Riesgo:** Medio — requiere actualizar imports en `pdf_ruta.py` y `economia_ruta.py`.

---

## 3.4 tenant_repository.py

### ¿Es importado en algún servicio o ruta?

**Sí — es importado en 5 repositorios y en los tests:**

### Lista de archivos que lo importan

**Repositorios (importan y heredan de `TenantRepository`):**
1. `app/repositorios/movimiento_caja_repository.py` — línea 18
2. `app/repositorios/vehiculo_repository.py` — línea 9
3. `app/repositorios/ticket_repository.py` — línea 14
4. `app/repositorios/notificacion_repository.py` — línea 15
5. `app/repositorios/cita_repository.py` — línea 11

**Tests:**
6. `tests/test_tenant_isolation.py` — línea 39 (importa directamente para tests de aislamiento)

**Servicios y rutas:** No importan `tenant_repository.py` directamente — lo usan
indirectamente a través de los repositorios que heredan de él.

### Recomendación

**Mantener `tenant_repository.py`** — es una clase base activa y fundamental para el
aislamiento multi-tenant. Es importada por 5 repositorios que heredan de ella para garantizar
que todas las queries incluyan el filtro `taller_id` automáticamente.

Es uno de los archivos más importantes del sistema desde el punto de vista de seguridad.
No es código muerto — es infraestructura de seguridad.

---

## 3.5 Patrón de validación taller_id duplicado

### Análisis del patrón

El patrón descrito en el spec (fetch por ID sin filtro de taller, luego comparación manual)
**aparece de forma limitada** en el código. La mayoría de los archivos ya usan el patrón
correcto de incluir `taller_id` directamente en el filtro de la query.

### Lista de archivos y líneas donde aparece el patrón

#### Patrón exacto (fetch sin taller_id + comparación posterior):

**1. `app/rutas/ticket_ruta.py` — líneas 73-76**
```python
def _obtener_ticket_del_taller_o_404(db: Session, ticket_id: int, taller_id: int) -> Ticket:
    """Obtiene un ticket verificando que pertenezca al taller del usuario autenticado."""
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket or ticket.taller_id != taller_id:
        raise HTTPException(status_code=404, detail="Ticket no encontrado")
    return ticket
```
Este es el único lugar donde aparece el patrón exacto `objeto.taller_id != taller_id`.

#### Patrón relacionado — fetch sin taller_id en mobile_api_ruta.py (problema de seguridad):

`app/rutas/mobile_api_ruta.py` tiene **múltiples endpoints** que hacen fetch de tickets
**sin filtrar por taller_id** en la query:

| Línea | Endpoint | Patrón |
|---|---|---|
| 82-84 | `GET /tickets/{ticket_id}` | `db.query(Ticket).filter(Ticket.id == ticket_id).first()` |
| 111-113 | `GET /tickets/{ticket_id}/procesos` | `db.query(Ticket).filter(Ticket.id == ticket_id).first()` |
| 132-134 | `POST /tickets/{ticket_id}/procesos` | `db.query(Ticket).filter(Ticket.id == ticket_id).first()` |
| 168-170 | `POST /tickets/{ticket_id}/procesos/con-foto` | `db.query(Ticket).filter(Ticket.id == ticket_id).first()` |
| 210-212 | `GET /tickets/{ticket_id}/repuestos` | `db.query(Ticket).filter(Ticket.id == ticket_id).first()` |
| 223-225 | `POST /tickets/{ticket_id}/repuestos` | `db.query(Ticket).filter(Ticket.id == ticket_id).first()` |
| 253-255 | `GET /tickets/{ticket_id}/fotos` | `db.query(Ticket).filter(Ticket.id == ticket_id).first()` |
| 281-283 | `PATCH /tickets/{ticket_id}/estado` | `db.query(Ticket).filter(Ticket.id == ticket_id).first()` |
| 317-319 | `GET /tickets/{ticket_id}/resumen` | `db.query(Ticket).filter(Ticket.id == ticket_id).first()` |
| 400-402 | `POST /tickets/{ticket_id}/fotos` | `db.query(Ticket).filter(Ticket.id == ticket_id).first()` |
| 434-436 | `POST /tickets/{ticket_id}/entregar` | `db.query(Ticket).filter(Ticket.id == ticket_id).first()` |
| 494-496 | `GET /tickets/{ticket_id}/compras` | `db.query(Ticket).filter(Ticket.id == ticket_id).first()` |
| 510-512 | `POST /tickets/{ticket_id}/compras` | `db.query(Ticket).filter(Ticket.id == ticket_id).first()` |
| 573-575 | `POST /tickets/{ticket_id}/cobros` | `db.query(Ticket).filter(Ticket.id == ticket_id).first()` |
| 602-605 | `PATCH /tickets/{ticket_id}/finanzas` | `db.query(Ticket).filter(Ticket.id == ticket_id).first()` |
| 756-759 | `POST /sync/batch` (loop) | `db.query(Ticket).filter(Ticket.id == op.ticket_id).first()` |

**Nota importante:** En `mobile_api_ruta.py` estos endpoints están protegidos por
`requerir_password_admin` (contraseña de admin), no por JWT con `taller_id`. Por eso no
aplican el filtro de tenant — la app móvil opera con una contraseña de taller única, no con
JWT multi-tenant. Esto es una decisión de diseño, no un bug, pero implica que la app móvil
no tiene aislamiento multi-tenant real.

#### Patrón correcto ya aplicado (para referencia):

Los siguientes archivos ya usan el patrón correcto de incluir `taller_id` en la query:
- `app/rutas/citas_ruta.py` — `Cita.taller_id == taller_id` en el filtro
- `app/rutas/vehiculo_ruta.py` — `Vehiculo.taller_id == taller_id` en el filtro
- `app/rutas/movimiento_caja_ruta.py` — `MovimientoCaja.taller_id == taller_id` en el filtro
- `app/rutas/configuracion_ruta.py` — `Mecanico.taller_id == taller_id` en el filtro
- Todos los repositorios que heredan de `TenantRepository` — filtro automático

### Total de ocurrencias

| Tipo de patrón | Ocurrencias | Archivos |
|---|---|---|
| Patrón exacto (fetch + comparación `!=`) | **1** | `ticket_ruta.py` línea 74 |
| Fetch sin taller_id en mobile (sin JWT) | **16** | `mobile_api_ruta.py` |
| **Total** | **17** | 2 archivos |

### Recomendación

**Para `ticket_ruta.py` (línea 73-76):**
La función `_obtener_ticket_del_taller_o_404()` ya es un helper centralizado — es exactamente
el patrón `tenant_guard` que se propone crear. Se puede refactorizar para usar
`TenantRepository.get_by_id()` que ya aplica el filtro automáticamente, o mantenerla como
está ya que está encapsulada en una función helper.

**Para `mobile_api_ruta.py`:**
Los 16 casos son intencionales — la app móvil usa autenticación por contraseña de admin
(`requerir_password_admin`), no JWT con `taller_id`. Esto significa que la app móvil opera
sobre **todos los tickets del sistema sin filtro de taller**. Esto es un riesgo de seguridad
multi-tenant si el sistema escala a múltiples talleres.

**Acción recomendada para Fase 3C:**
1. Crear `app/utils/tenant_guard.py` con `verificar_pertenencia(objeto, taller_id, nombre)`.
2. Reemplazar el patrón en `ticket_ruta.py` línea 74 con la llamada al helper.
3. Evaluar si `mobile_api_ruta.py` debe recibir `taller_id` del token de QR para aplicar
   aislamiento multi-tenant en la app móvil (cambio de diseño mayor, Fase 3C alto riesgo).

---

## Resumen de hallazgos

| Subtarea | Hallazgo | Severidad | Acción |
|---|---|---|---|
| 3.1 Rutas mobile | `mobile_ruta.py` no registrado, redundante | Alto | Eliminar |
| 3.1 Rutas mobile | `mobile_ruta.py` expone tickets sin auth | Crítico | Eliminar urgente |
| 3.2 WhatsApp | Arquitectura Strategy correcta | — | Mantener |
| 3.3 PDF | `imagen_escalada()` y `fmt_cop()` duplicadas | Medio | Extraer a `pdf_utils.py` |
| 3.3 PDF | Paleta de colores duplicada | Bajo | Extraer a `pdf_utils.py` |
| 3.4 tenant_repository | Activo, heredado por 5 repositorios | — | Mantener |
| 3.5 Patrón taller_id | 1 ocurrencia exacta en `ticket_ruta.py` | Bajo | Refactorizar con tenant_guard |
| 3.5 Patrón taller_id | 16 ocurrencias en `mobile_api_ruta.py` sin filtro tenant | Alto | Evaluar diseño multi-tenant móvil |
