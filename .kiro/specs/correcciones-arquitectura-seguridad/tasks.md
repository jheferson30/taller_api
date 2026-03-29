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

- [x] 5. Fix: contraseñas hardcodeadas en conftest.py

  - [x] 5.1 Crear .env.test y excluirlo de git
    - Crear `.env.test` en la raíz del proyecto con `PDF_PASSWORD` y `ADMIN_PASSWORD` con valores reales de test
    - Verificar que `.gitignore` incluye `.env.test`
    - Crear `.env.test.example` con valores placeholder como documentación para otros desarrolladores
    - _Bug_Condition: isBugCondition(X) donde X es conftest.py con "1234" hardcodeado — cualquiera que lea el repo conoce las contraseñas_
    - _Requirements: 1.8_

  - [x] 5.2 Actualizar conftest.py para leer desde .env.test
    - En `tests/conftest.py`: agregar `from dotenv import load_dotenv` y llamar a `load_dotenv(".env.test", override=False)` antes de los `setdefault`
    - Reemplazar `os.environ.setdefault("PDF_PASSWORD", "1234")` por `os.environ.setdefault("PDF_PASSWORD", "")` (sin valor hardcodeado)
    - Reemplazar `os.environ.setdefault("ADMIN_PASSWORD", "1234")` de la misma forma
    - Agregar comentario explicando el fallback vacío para CI
    - _Expected_Behavior: conftest.py no contiene contraseñas hardcodeadas; las lee desde .env.test o variables de entorno del sistema_
    - _Preservation: los tests existentes siguen pasando cuando .env.test está presente (3.8)_
    - _Requirements: 2.8, 3.8_

  - [x] 5.3 Verificar que los tests siguen pasando con la nueva configuración
    - Ejecutar la suite de tests completa y confirmar que todos pasan
    - Verificar que `.env.test` no aparece en `git status`
    - _Requirements: 3.8_

- [x] 6. Fix: implementar rate limiting con slowapi

  - [x] 6.1 Configurar slowapi en app/main.py
    - Importar `Limiter`, `_rate_limit_exceeded_handler` desde `slowapi`; `get_remote_address` desde `slowapi.util`; `RateLimitExceeded` desde `slowapi.errors`
    - Crear instancia: `limiter = Limiter(key_func=get_remote_address)`
    - Registrar en el estado de la app: `app.state.limiter = limiter`
    - Registrar el handler de error 429: `app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)`
    - _Bug_Condition: isBugCondition(X) donde X es el arranque de la app — slowapi está en requirements.txt pero no configurado_
    - _Requirements: 1.9_

  - [x] 6.2 Aplicar rate limiting a endpoints sensibles
    - En `app/rutas/ticket_ruta.py → generar_pdf_cliente()`: agregar `@limiter.limit("20/minute")` y el parámetro `request: Request`
    - En `app/rutas/mobile_api_ruta.py → actualizar_estado_mobile()`: agregar `@limiter.limit("30/minute")` y el parámetro `request: Request`
    - Importar `limiter` desde `app.main` en los routers que lo necesiten, o bien definir el limiter en un módulo compartido (ej. `app/configuracion/limiter.py`) para evitar imports circulares
    - _Expected_Behavior: petición que supera el límite → 429 Too Many Requests; petición dentro del límite → procesada normalmente_
    - _Preservation: peticiones dentro del límite siguen funcionando sin cambios (3.9)_
    - _Requirements: 2.9, 3.9_

  - [x] 6.3 Verificar que el rate limiting funciona correctamente
    - Escribir un test que envíe más peticiones que el límite configurado y verifique que la petición que excede el límite retorna 429
    - Verificar que peticiones dentro del límite retornan respuestas normales
    - _Requirements: 2.9, 3.9_

- [x] 7. Fix: consolidar N+1 queries en obtener_resumen_ticket

  - [x] 7.1 Refactorizar obtener_resumen_ticket con queries agregadas
    - En `app/rutas/mobile_api_ruta.py → obtener_resumen_ticket()`: importar `func` desde `sqlalchemy`
    - Reemplazar las 4 queries `COUNT` separadas por queries individuales usando `func.count()` con `.scalar()`
    - Reemplazar la carga completa de compras para sumar valores por `db.query(func.coalesce(func.sum(TicketCompra.valor), 0)).filter(TicketCompra.ticket_id == ticket_id).scalar()`
    - Reemplazar la carga completa de cobros para sumar valores por `db.query(func.coalesce(func.sum(TicketCobro.valor), 0)).filter(TicketCobro.ticket_id == ticket_id).scalar()`
    - Mantener exactamente la misma estructura de respuesta JSON
    - _Bug_Condition: isBugCondition(X) donde X es cualquier llamada a GET /api/mobile/tickets/{id}/resumen — ejecuta 6 queries en lugar de queries con agregaciones_
    - _Expected_Behavior: el endpoint usa func.count() y func.sum() en lugar de cargar todos los registros en memoria_
    - _Preservation: la respuesta JSON retorna exactamente los mismos valores que antes (3.10)_
    - _Requirements: 1.10, 2.10, 3.10_

  - [x] 7.2 Verificar que la respuesta es idéntica a la implementación original
    - Escribir un test que verifique que `contadores.procesos`, `contadores.repuestos`, `contadores.fotos`, `contadores.compras`, `finanzas.total_egresos` y `finanzas.total_cobros` son correctos con datos reales
    - _Requirements: 3.10_

- [x] 8. Fix: mover schemas Pydantic a app/esquemas/mobile_schema.py

  - [x] 8.1 Crear app/esquemas/mobile_schema.py con los schemas extraídos
    - Crear `app/esquemas/mobile_schema.py`
    - Mover los 14 schemas desde `mobile_api_ruta.py`: `TicketListResponse`, `TicketDetailResponse`, `ProcesoResponse`, `RepuestoResponse`, `FotoResponse`, `ProcesoCreate`, `RepuestoCreate`, `ActualizarEstadoTicket`, `CompraResponse`, `CompraCreate`, `CobroResponse`, `CobroCreate`, `ActualizarFinanzasData`, `EntregarTicketData`
    - Agregar los imports necesarios (`BaseModel`, `Optional`, `datetime`, etc.) en el nuevo archivo
    - _Bug_Condition: isBugCondition(X) donde X es la definición de schemas en mobile_api_ruta.py — viola separación de responsabilidades_
    - _Requirements: 1.11_

  - [x] 8.2 Actualizar mobile_api_ruta.py para importar desde mobile_schema.py
    - En `app/rutas/mobile_api_ruta.py`: eliminar las 14 definiciones de schemas inline
    - Agregar import: `from app.esquemas.mobile_schema import (TicketListResponse, TicketDetailResponse, ProcesoResponse, RepuestoResponse, FotoResponse, ProcesoCreate, RepuestoCreate, ActualizarEstadoTicket, CompraResponse, CompraCreate, CobroResponse, CobroCreate, ActualizarFinanzasData, EntregarTicketData)`
    - _Expected_Behavior: mobile_api_ruta.py importa schemas desde app.esquemas.mobile_schema; los schemas son reutilizables desde cualquier módulo_
    - _Preservation: todos los endpoints del router siguen funcionando con los mismos schemas y validaciones (3.11)_
    - _Requirements: 2.11, 3.11_

  - [x] 8.3 Verificar que el router funciona correctamente tras la extracción
    - Ejecutar los tests existentes del router mobile y confirmar que todos pasan
    - Verificar que `from app.esquemas.mobile_schema import TicketListResponse` funciona sin importar el router
    - _Requirements: 3.11_


