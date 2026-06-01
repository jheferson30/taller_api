# Hallazgos a Resolver — Auditoría Backend

**Fecha:** 2026-04-25  
**Fuente:** Auditoría automatizada Fase 1 (Tarea 2)  
**Estado:** Pendiente de resolución

---

## Resumen

| Severidad | Total | Resueltos |
|-----------|-------|-----------|
| 🔴 Crítico | 9 | 0 |
| 🟠 Alto | 4 | 0 |
| 🟡 Medio | 6 | 0 |
| 🔵 Bajo | 4 | 0 |

---

## 🔴 CRÍTICOS — Resolver antes de cualquier otra tarea

### C-01 · `mobile_ruta.py` — Tickets activos sin autenticación ni filtro taller_id

- **Archivo:** `app/rutas/mobile_ruta.py` línea 18
- **Endpoint:** `GET /mobile/v1/tickets/activos`
- **Problema:** Sin autenticación. La query `db.query(Ticket).filter(Ticket.estado.in_([...]))` no filtra por `taller_id`. Devuelve tickets de **todos** los talleres a cualquier persona sin token.
- **Fix:** Agregar `@require_auth` (o `Depends(requerir_password_admin)`). Agregar filtro `Ticket.taller_id == request.state.taller_id`.
- **Fuente:** security-auth-report.txt, security-tenant-queries-report.txt

---

### C-02 · `mobile_ruta.py` — Timeline de ticket sin autenticación ni verificación de taller

- **Archivo:** `app/rutas/mobile_ruta.py` líneas 42–57
- **Endpoint:** `GET /mobile/v1/tickets/{ticket_id}/timeline`
- **Problema:** Sin autenticación. Las queries de `TicketProceso` y `TicketFoto` no verifican que el ticket pertenezca al taller del usuario. Cualquiera puede ver el timeline de cualquier ticket con solo conocer el `ticket_id`.
- **Fix:** Agregar autenticación. Verificar `ticket.taller_id == request.state.taller_id` antes de devolver datos.
- **Fuente:** security-auth-report.txt, security-tenant-queries-report.txt

---

### C-03 · `whatsapp_ruta.py` — Envío de WhatsApp sin autenticación

- **Archivo:** `app/rutas/whatsapp_ruta.py` líneas 70 y 88
- **Endpoints:** `POST /api/mobile/tickets/{id}/whatsapp`, `POST /api/whatsapp/tickets/{id}/mensaje`
- **Problema:** Sin autenticación. Cualquier persona puede enviar mensajes de WhatsApp en nombre de cualquier taller. Además, se usa `ticket.taller_id` de la BD sin verificar contra el JWT.
- **Fix:** Agregar `@require_auth`. Verificar `ticket.taller_id == request.state.taller_id` después de obtener el ticket.
- **Fuente:** security-auth-report.txt, security-taller-id-report.txt

---

### C-04 · `whatsapp_ruta.py` — Logs de notificaciones sin autenticación ni filtro taller_id

- **Archivo:** `app/rutas/whatsapp_ruta.py` línea 109
- **Endpoint:** `GET /api/mobile/whatsapp/logs`
- **Problema:** Sin autenticación. La query `db.query(LogNotificacion)` devuelve logs de **todos** los talleres sin filtrar.
- **Fix:** Agregar `@require_auth`. Agregar filtro `LogNotificacion.taller_id == request.state.taller_id`.
- **Fuente:** security-auth-report.txt, security-tenant-queries-report.txt

---

### C-05 · `whatsapp_ruta.py` — Webhook routing incorrecto (multi-taller)

- **Archivo:** `app/rutas/whatsapp_ruta.py` línea ~47
- **Endpoint:** `POST /whatsapp/webhook` (webhook entrante de WhatsApp)
- **Problema:** La query obtiene la **primera** `ConfiguracionTaller` con WhatsApp configurado, sin filtrar por número de teléfono. Con múltiples talleres, todos los mensajes entrantes se asocian al mismo taller.
- **Fix:** Implementar routing por número de teléfono: filtrar `ConfiguracionTaller` por el número de destino del mensaje entrante (`To` en el payload de Twilio/Meta).
- **Fuente:** security-tenant-queries-report.txt

---

### C-06 · `economia_ruta.py` — Datos financieros sin filtro taller_id

- **Archivo:** `app/rutas/economia_ruta.py` líneas 20–80
- **Funciones:** `_base_query_dia()`, `_sumar_por_tipo()` y otros helpers
- **Problema:** Las queries de `MovimientoCaja` no filtran por `taller_id`. La contraseña admin es global (no por taller), por lo que cualquier admin puede ver los datos financieros de todos los talleres.
- **Fix:** Agregar `taller_id` como parámetro a los helpers. Obtenerlo del JWT (`request.state.taller_id`) y pasarlo a cada query.
- **Fuente:** security-tenant-queries-report.txt

---

### C-07 · `whatsapp_ruta.py` — `ticket.taller_id` usado sin verificación contra JWT

- **Archivo:** `app/rutas/whatsapp_ruta.py` líneas ~80 y ~100
- **Funciones:** `enviar_whatsapp_mobile()`, `enviar_whatsapp_web()`
- **Problema:** Se pasa `ticket.taller_id` al servicio sin verificar que coincida con `request.state.taller_id`. Combinado con la falta de autenticación (C-03), permite operar sobre tickets de cualquier taller.
- **Fix:** Después de agregar auth (C-03), agregar: `if ticket.taller_id != request.state.taller_id: raise HTTPException(404)`.
- **Fuente:** security-taller-id-report.txt
- **Nota:** Este fix es consecuencia de C-03 — resolverlos juntos.

---

### C-08 · `mobile_ruta.py` — Ausencia total de filtro taller_id en todas las queries

- **Archivo:** `app/rutas/mobile_ruta.py`
- **Problema:** Ninguna query en este archivo filtra por `taller_id`. El archivo completo viola el aislamiento multi-tenant.
- **Fix:** Revisar si este archivo es el activo (vs `mobile_api_ruta.py` que sí tiene auth). Si es redundante, eliminarlo (Tarea 3.1 del plan). Si es necesario, corregir todos sus endpoints.
- **Fuente:** security-tenant-queries-report.txt
- **Nota:** Relacionado con C-01 y C-02. Posiblemente este archivo sea el candidato a eliminar en Tarea 3.1.

---

### C-09 · `pdf_ruta.py` — `TicketRepository` instanciado sin `taller_id`

- **Archivo:** `app/rutas/pdf_ruta.py` línea ~43
- **Función:** `generate_ticket_pdf()`
- **Problema:** `TicketRepository(db)` se instancia sin `taller_id`, violando el contrato de `TenantRepository`. Puede devolver datos de cualquier taller o fallar en runtime.
- **Fix:** Agregar autenticación al endpoint. Instanciar con `TicketRepository(db, taller_id=request.state.taller_id)`.
- **Fuente:** security-tenant-queries-report.txt

---

## 🟠 ALTOS — Resolver en la misma iteración que los críticos

### A-01 · `upload_ruta.py` — Endpoints de subida sin `@require_auth` explícito

- **Archivo:** `app/rutas/upload_ruta.py` líneas 32, 61, 89
- **Endpoints:** `POST /upload/foto`, `POST /upload/compra`, `POST /upload/firma`
- **Problema:** Los endpoints usan `request.state.taller_id` (implica que el middleware procesó el token), pero no tienen `@require_auth` como decorador explícito. Si el middleware falla o se bypasea, no hay segunda línea de defensa.
- **Fix:** Agregar `@require_auth` a los tres endpoints POST.
- **Fuente:** security-auth-report.txt

---

### A-02 · `upload_ruta.py` — Archivos servidos sin autenticación

- **Archivo:** `app/rutas/upload_ruta.py` líneas 117, 127, 137
- **Endpoints:** `GET /upload/fotos/{taller_id}/{filename}`, `/compras/...`, `/firmas/...`
- **Problema:** Los archivos son accesibles públicamente si se conoce el `taller_id` y el nombre del archivo. El `taller_id` viene del path (no del JWT).
- **Fix:** Evaluar si deben ser públicos (para mostrar fotos en la app del cliente) o protegidos. Si son protegidos, agregar auth y verificar que `taller_id` del path coincida con el del JWT.
- **Fuente:** security-auth-report.txt

---

### A-03 · `pdf_ruta.py` — Endpoints de PDF sin autenticación

- **Archivo:** `app/rutas/pdf_ruta.py` líneas 20, ~61, ~109
- **Endpoints:** `POST /pdf/tickets/{id}/generate`, `GET /pdf/tasks/{id}/status`, `GET /pdf/download/{filename}`
- **Problema:** Cualquier persona puede generar PDFs de cualquier ticket y descargar PDFs generados sin autenticarse.
- **Fix:** Agregar `@require_auth` o `Depends(requerir_password_admin)` a los tres endpoints.
- **Fuente:** security-auth-report.txt

---

### A-04 · `main.py` y `health.py` — `urllib.request.urlopen` duplicado

- **Archivos:** `app/main.py` línea 720, `app/rutas/health.py` línea 25
- **Problema:** La función `_get_ip_local()` está duplicada en ambos archivos usando `urllib.request.urlopen` (marcado por bandit como riesgo). Código duplicado + dependencia de servicio externo sin manejo de error robusto.
- **Fix:** Extraer a un helper en `app/utils/` usando `httpx` con timeout y manejo de error explícito. Importar desde ambos archivos.
- **Fuente:** bandit-report.txt

---

## 🟡 MEDIOS — Resolver antes de las fases 3B/3C

### M-01 · `seguridad_ruta.py` — `cambiar_password_admin` sin `@require_auth`

- **Archivo:** `app/rutas/seguridad_ruta.py` línea 161
- **Endpoint:** `POST /seguridad/admin/cambiar-password`
- **Problema:** Verifica el rol ADMIN manualmente dentro de la función, sin `@require_auth` como decorador. Si el middleware falla, la verificación manual podría no ejecutarse.
- **Fix:** Agregar `@require_auth` como decorador explícito.
- **Fuente:** security-auth-report.txt

---

### M-02 · `ticket_ruta.py` — Múltiples endpoints sin `@require_auth` explícito

- **Archivo:** `app/rutas/ticket_ruta.py` líneas 89, 94, 197, 253 y más
- **Problema:** Los endpoints usan `request.state.taller_id` (implica auth del middleware) pero no tienen `@require_auth` explícito. El endpoint `/procesos-rapidos` devuelve una lista hardcodeada sin ninguna auth.
- **Fix:** Agregar `@require_auth` a todos los endpoints que acceden a datos del taller. Evaluar si `/procesos-rapidos` debe ser público o protegido.
- **Fuente:** security-auth-report.txt

---

### M-03 · `configuracion_ruta.py` — `listar_mecanicos` sin `@require_auth` explícito

- **Archivo:** `app/rutas/configuracion_ruta.py` línea ~54
- **Endpoint:** `GET /configuracion/mecanicos`
- **Problema:** Usa `request.state.taller_id` sin `@require_auth` explícito. Inconsistente con el resto del archivo que usa `Depends(verificar_admin)`.
- **Fix:** Agregar `@require_auth` explícito para consistencia.
- **Fuente:** security-auth-report.txt

---

### M-04 · `pdf_economia.py` — `except Exception: pass` sin logging

- **Archivo:** `app/utils/pdf_economia.py` línea 159
- **Problema:** Excepción silenciada en carga de imagen. Si falla la carga de una imagen en el PDF, el error se ignora silenciosamente sin ningún registro.
- **Fix:** Reemplazar `except Exception: pass` por `except Exception as e: logger.warning(f"Error cargando imagen en PDF: {e}")`.
- **Fuente:** bandit-report.txt

---

### M-05 · `pdf_generator.py` — `except Exception: pass` sin logging (x2)

- **Archivo:** `app/utils/pdf_generator.py` líneas 213 y 353
- **Problema:** Dos excepciones silenciadas en generación de PDF sin ningún registro.
- **Fix:** Mismo patrón que M-04 — agregar `logger.warning()` con el error capturado.
- **Fuente:** bandit-report.txt

---

### M-06 · `seguridad_ruta.py` — Endpoints de economía sin documentación de intencionalidad

- **Archivo:** `app/rutas/seguridad_ruta.py` líneas 56, 62, 93, 115, 153
- **Endpoints:** `/seguridad/economia/*` y `/seguridad/admin/tiene-password-bd`
- **Problema:** Son intencionalmente públicos (sistema de contraseña local, no JWT), pero no están documentados como tal. Cualquier revisor de seguridad los marcará como vulnerabilidades.
- **Fix:** Agregar comentario explícito en cada endpoint: `# Público por diseño — usa contraseña local, no JWT. Ver design.md sección X.`
- **Fuente:** security-auth-report.txt

---

## 🔵 BAJOS — Resolver en limpieza general

### B-01 · `pdf_generator.py` — Complejidad ciclomática crítica (CC=77)

- **Archivo:** `app/utils/pdf_generator.py` línea 114
- **Función:** `generar_pdf_ticket_completo`
- **Problema:** Complejidad ciclomática de 77 (grado F). Extremadamente difícil de mantener y testear. Cualquier cambio en esta función tiene alto riesgo de introducir bugs.
- **Fix:** Refactorizar extrayendo secciones del PDF en funciones privadas: `_generar_encabezado()`, `_generar_tabla_procesos()`, `_generar_tabla_repuestos()`, `_generar_pie_pagina()`, etc.
- **Fuente:** radon-report.txt

---

### B-02 · `pdf_economia.py` — Complejidad ciclomática muy alta (CC=49)

- **Archivo:** `app/utils/pdf_economia.py` línea 70
- **Función:** `generar_pdf_economia_profesional`
- **Problema:** Complejidad ciclomática de 49 (grado F). Mismo problema que B-01.
- **Fix:** Mismo enfoque — extraer secciones en funciones privadas.
- **Fuente:** radon-report.txt

---

### B-03 · `auth_middleware.py` — Complejidad alta (CC=28)

- **Archivo:** `app/seguridad/auth_middleware.py` línea 52
- **Función:** `AuthMiddleware.dispatch`
- **Problema:** Complejidad ciclomática de 28 (grado D). El middleware de auth maneja demasiados casos en una sola función.
- **Fix:** Extraer lógica de validación de token, manejo de rutas públicas y manejo de errores en métodos privados del middleware.
- **Fuente:** radon-report.txt

---

### B-04 · `mobile_api_ruta.py` — `sincronizar_operaciones_batch` con CC=29

- **Archivo:** `app/rutas/mobile_api_ruta.py` línea 713
- **Función:** `sincronizar_operaciones_batch`
- **Problema:** Complejidad ciclomática de 29 (grado D). Función de sincronización batch con demasiada lógica condicional.
- **Fix:** Extraer el procesamiento de cada tipo de operación en funciones separadas: `_procesar_operacion_ticket()`, `_procesar_operacion_proceso()`, etc.
- **Fuente:** radon-report.txt

---

## Orden de resolución recomendado

```
Iteración 1 (seguridad crítica — hacer YA):
  C-01, C-02  →  mobile_ruta.py: auth + filtro taller_id
  C-03, C-07  →  whatsapp_ruta.py: auth + verificación taller_id (juntos)
  C-04        →  whatsapp_ruta.py: logs con auth + filtro taller_id
  C-05        →  whatsapp_ruta.py: webhook routing por teléfono
  C-06        →  economia_ruta.py: filtro taller_id en helpers
  C-08        →  mobile_ruta.py: decisión de eliminar o corregir (ver Tarea 3.1)
  C-09        →  pdf_ruta.py: TicketRepository con taller_id

Iteración 2 (auth faltante — alta prioridad):
  A-01        →  upload_ruta.py: @require_auth en POST
  A-02        →  upload_ruta.py: decisión sobre GET de archivos
  A-03        →  pdf_ruta.py: auth en todos los endpoints
  A-04        →  main.py + health.py: consolidar _get_ip_local con httpx

Iteración 3 (antipatrones — antes de fases 3B/3C):
  M-01        →  seguridad_ruta.py: @require_auth en cambiar_password_admin
  M-02        →  ticket_ruta.py: @require_auth explícito en todos los endpoints
  M-03        →  configuracion_ruta.py: @require_auth en listar_mecanicos
  M-04, M-05  →  pdf_economia.py + pdf_generator.py: logging en except
  M-06        →  seguridad_ruta.py: documentar endpoints públicos intencionales

Iteración 4 (deuda técnica — junto con fases 3B/3C):
  B-01, B-02  →  pdf_generator.py + pdf_economia.py: refactorizar CC
  B-03        →  auth_middleware.py: refactorizar dispatch
  B-04        →  mobile_api_ruta.py: refactorizar sincronizar_operaciones_batch
```

---

## Archivos de reporte fuente

| Reporte | Ubicación |
|---------|-----------|
| Seguridad — auth faltante | `.kiro/specs/limpieza-codigo-completo/security-auth-report.txt` |
| Seguridad — queries sin taller_id | `.kiro/specs/limpieza-codigo-completo/security-tenant-queries-report.txt` |
| Seguridad — taller_id del cliente | `.kiro/specs/limpieza-codigo-completo/security-taller-id-report.txt` |
| Seguridad — role mixing | `.kiro/specs/limpieza-codigo-completo/security-role-mixing-report.txt` |
| Complejidad ciclomática | `.kiro/specs/limpieza-codigo-completo/radon-report.txt` |
| Seguridad general (bandit) | `.kiro/specs/limpieza-codigo-completo/bandit-report.txt` |
| Resumen ejecutivo | `.kiro/specs/limpieza-codigo-completo/audit-summary-2.md` |
