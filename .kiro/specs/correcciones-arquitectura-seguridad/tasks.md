# Implementation Plan

- [x] 1. Write bug condition exploration test
  - **Property 1: Bug Condition** - Lógica de finalización duplicada y datos ausentes en PDF
  - **CRITICAL**: Este test DEBE FALLAR en el código sin corregir — la falla confirma que los bugs existen
  - **DO NOT attempt to fix the test or the code when it fails**
  - **NOTE**: El test codifica el comportamiento esperado; validará el fix cuando pase tras la implementación
  - **GOAL**: Exponer contraejemplos que demuestren la existencia de los bugs
  - **Scoped PBT Approach**: Para bugs deterministas, acotar la propiedad a los casos concretos que fallan
  - Caso A — Duplicación de lógica: llamar `_finalizar_ticket` desde `ticket_ruta.py` y desde `mobile_api_ruta.py` con el mismo ticket y verificar que ambas rutas producen exactamente el mismo `saldo_pendiente` y el mismo `MovimientoCaja`. En el código actual no existe `_finalizar_ticket`, por lo que la función no es importable → test falla.
  - Caso B — PDF sin propietario: construir un `ticket_dict` con `vehiculo_id` apuntando a un vehículo con `nombre_propietario="Juan"` y `telefono_propietario="3001234567"`, llamar al endpoint `GET /tickets/{id}/pdf` y verificar que el PDF contiene esos valores. En el código actual `hasattr(ticket, 'nombre_propietario')` siempre es `False` → los campos quedan vacíos → test falla.
  - Run test on UNFIXED code
  - **EXPECTED OUTCOME**: Test FAILS (esto es correcto — prueba que los bugs existen)
  - Documentar los contraejemplos encontrados para entender la causa raíz
  - Marcar tarea completa cuando el test esté escrito, ejecutado y la falla documentada
  - _Requirements: 1.1, 1.2, 1.7_

- [x] 2. Write preservation property tests (BEFORE implementing fix)
  - **Property 2: Preservation** - Comportamiento existente de finalización y otros routers
  - **IMPORTANT**: Seguir la metodología observation-first
  - Observar en el código sin corregir: `POST /tickets/{id}/finalizar` con `total_servicio=100000` y `anticipo_recibido=20000` retorna `saldo_pendiente=80000` y crea un `MovimientoCaja` de tipo `INGRESO_FINAL` con `valor=80000`
  - Observar: `POST /tickets/{id}/finalizar` sin `total_servicio` retorna `400 Bad Request`
  - Observar: endpoints de economía, vehículos, citas y seguridad responden normalmente (no se ven afectados)
  - Escribir property-based tests: para todo ticket con `total_servicio > 0`, `saldo_pendiente = max(0, total_servicio - anticipo_recibido - total_cobros)` (desde Preservation Requirements en bugfix.md)
  - Escribir test: ticket sin `total_servicio` → siempre `400`
  - Verificar que los tests PASAN en el código sin corregir
  - **EXPECTED OUTCOME**: Tests PASS (confirma el comportamiento base a preservar)
  - Marcar tarea completa cuando los tests estén escritos, ejecutados y pasando en código sin corregir
  - _Requirements: 3.1, 3.2, 3.3, 3.5, 3.6_

- [x] 3. Fix: correcciones de arquitectura, seguridad y datos

  - [x] 3.1 Extraer lógica de finalización a función compartida en ticket_service.py
    - Crear `app/servicios/ticket_service.py` con función `finalizar_ticket(ticket, db) -> Ticket`
    - La función debe: validar `total_servicio`, calcular `saldo_pendiente = max(0, total_servicio - anticipo - total_cobros)`, actualizar `ticket.estado = "FINALIZADO"`, `ticket.fecha_cierre`, crear `MovimientoCaja(tipo=INGRESO_FINAL, valor=total_servicio - anticipo)` si `valor_ingreso > 0`
    - Reemplazar el bloque de finalización en `ticket_ruta.py → finalizar_ticket()` por una llamada a `ticket_service.finalizar_ticket(ticket, db)`
    - Reemplazar el bloque de finalización en `mobile_api_ruta.py → actualizar_estado_mobile()` (bloque `if data.estado == "FINALIZADO"`) por una llamada a `ticket_service.finalizar_ticket(ticket, db)`
    - _Bug_Condition: isBugCondition(X) donde X es cualquier llamada a finalizar ticket — la lógica existe duplicada en ticket_ruta.py y mobile_api_ruta.py sin función compartida_
    - _Expected_Behavior: ambas rutas invocan `ticket_service.finalizar_ticket(ticket, db)` y producen resultados idénticos_
    - _Preservation: saldo_pendiente = max(0, total_servicio - anticipo - cobros); MovimientoCaja INGRESO_FINAL creado; 400 si no hay total_servicio_
    - _Requirements: 2.1, 2.2, 3.1, 3.2, 3.3_

  - [x] 3.2 Eliminar router dead code /mobile/v1
    - En `app/main.py`: eliminar la línea `app.include_router(mobile_ruta.router)`
    - En `app/main.py`: eliminar `mobile_ruta` del import de `app.rutas`
    - Verificar que los endpoints `/mobile/v1/health`, `/mobile/v1/tickets/activos` y `/mobile/v1/tickets/{id}/timeline` ya no están registrados (retornan 404)
    - El archivo `app/rutas/mobile_ruta.py` puede conservarse o eliminarse; lo mínimo es desregistrar el router
    - _Bug_Condition: isBugCondition(X) donde X es el arranque de la app — mobile_ruta.router está registrado en main.py_
    - _Expected_Behavior: la app arranca sin registrar el prefijo /mobile/v1_
    - _Preservation: todos los demás routers siguen funcionando normalmente_
    - _Requirements: 2.3, 3.6_

  - [x] 3.3 Agregar dependencia de autenticación a endpoints de tickets
    - En `app/rutas/ticket_ruta.py`: agregar `from app.seguridad.dependencias import requerir_password_admin` (o la dependencia apropiada según design.md)
    - Agregar `dependencies=[Depends(requerir_password_admin)]` al `APIRouter` de tickets, o bien como parámetro en cada endpoint según la granularidad definida en design.md
    - En `app/rutas/mobile_api_ruta.py`: aplicar la misma dependencia de autenticación al router `/api/mobile`
    - Verificar que una petición sin cabecera de autenticación a `/tickets` retorna `401 Unauthorized`
    - Verificar que una petición sin cabecera de autenticación a `/api/mobile/tickets` retorna `401 Unauthorized`
    - _Bug_Condition: isBugCondition(X) donde X es cualquier petición a /tickets o /api/mobile/tickets — no hay verificación de credenciales_
    - _Expected_Behavior: petición sin auth → 401; petición con auth correcta → procesada normalmente_
    - _Preservation: clientes autenticados correctamente siguen recibiendo respuestas normales (3.5)_
    - _Requirements: 2.4, 2.5, 3.5_

  - [x] 3.4 Hacer PDF_PASSWORD obligatoria desde variable de entorno
    - En `app/seguridad/dependencias.py`: cambiar `os.getenv("PDF_PASSWORD", "1234")` por `os.getenv("PDF_PASSWORD")` (sin valor por defecto)
    - Agregar validación al arranque: si `PDF_PASSWORD` es `None` o vacío, lanzar `RuntimeError("PDF_PASSWORD env var is required")` — puede hacerse en `dependencias.py` a nivel de módulo o en un evento `startup` en `main.py`
    - Aplicar el mismo criterio a `ADMIN_PASSWORD` si también usa `"1234"` como fallback
    - _Bug_Condition: isBugCondition(X) donde X es el arranque sin PDF_PASSWORD definida — el sistema usa "1234" hardcodeado_
    - _Expected_Behavior: arranque sin PDF_PASSWORD → error de configuración explícito; con PDF_PASSWORD definida → funciona normalmente_
    - _Preservation: cuando PDF_PASSWORD está definida, la validación de X-PDF-Password sigue funcionando igual (3.7)_
    - _Requirements: 2.6, 3.7_

  - [x] 3.5 Corregir PDF para mostrar nombre y teléfono del propietario
    - En `app/rutas/ticket_ruta.py → generar_pdf_cliente()`: después de obtener el ticket, consultar el vehículo: `vehiculo = db.query(Vehiculo).filter(Vehiculo.id == ticket.vehiculo_id).first()`
    - Reemplazar en `ticket_dict`:
      - `'nombre_propietario': ticket.nombre_propietario if hasattr(ticket, 'nombre_propietario') else None`
      - por: `'nombre_propietario': vehiculo.nombre_propietario if vehiculo else None`
      - `'telefono_propietario': ticket.telefono_propietario if hasattr(ticket, 'telefono_propietario') else None`
      - por: `'telefono_propietario': vehiculo.telefono_propietario if vehiculo else None`
    - Agregar import de `Vehiculo` si no existe en `ticket_ruta.py`
    - _Bug_Condition: isBugCondition(X) donde X es cualquier llamada a GET /tickets/{id}/pdf — `hasattr(ticket, 'nombre_propietario')` siempre False_
    - _Expected_Behavior: ticket_dict contiene nombre_propietario y telefono_propietario obtenidos del vehículo asociado_
    - _Preservation: cuando el vehículo tiene esos datos, el PDF los muestra en "INFORMACIÓN DEL VEHÍCULO Y TICKET" (3.4)_
    - _Requirements: 2.7, 3.4_

  - [x] 3.6 Verify bug condition exploration test now passes
    - **Property 1: Expected Behavior** - Lógica de finalización compartida y PDF con propietario
    - **IMPORTANT**: Re-ejecutar el MISMO test del paso 1 — NO escribir un test nuevo
    - El test del paso 1 codifica el comportamiento esperado
    - Cuando este test pase, confirma que el comportamiento esperado está satisfecho
    - Ejecutar el test de bug condition del paso 1
    - **EXPECTED OUTCOME**: Test PASSES (confirma que los bugs están corregidos)
    - _Requirements: 2.1, 2.2, 2.7_

  - [x] 3.7 Verify preservation tests still pass
    - **Property 2: Preservation** - Sin regresiones en finalización ni en otros routers
    - **IMPORTANT**: Re-ejecutar los MISMOS tests del paso 2 — NO escribir tests nuevos
    - Ejecutar los preservation property tests del paso 2
    - **EXPECTED OUTCOME**: Tests PASS (confirma que no hay regresiones)
    - Confirmar que todos los tests pasan tras el fix

- [x] 4. Checkpoint - Ensure all tests pass
  - Asegurarse de que todos los tests pasan. Consultar al usuario si surgen dudas.
