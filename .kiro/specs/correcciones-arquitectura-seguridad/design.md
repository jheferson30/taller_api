# Correcciones Arquitectura y Seguridad — Bugfix Design

## Overview

El backend FastAPI del taller mecánico presenta nueve problemas agrupados en tres categorías:
arquitectura (lógica duplicada, dead code, schemas inline), seguridad (endpoints sin autenticación,
passwords hardcodeados en código y en tests) y rendimiento/datos (PDF sin nombre/teléfono del
propietario, rate limiting no implementado, N+1 queries en resumen de ticket). El fix consolida la
lógica de finalización en una función compartida, elimina el router obsoleto, agrega autenticación a
los routers afectados, hace obligatorias las variables de entorno de seguridad, corrige la consulta
del vehículo en el PDF, mueve los schemas a su módulo dedicado, implementa rate limiting con slowapi
y consolida las queries de resumen con agregaciones SQLAlchemy.

---

## Glossary

- **Bug_Condition (C)**: Conjunto de condiciones que activan cada defecto descrito en este documento
- **Property (P)**: Comportamiento correcto esperado cuando la condición del bug se cumple
- **Preservation**: Comportamientos existentes que no deben cambiar tras el fix
- **`_finalizar_ticket(ticket, db)`**: Función compartida a extraer que encapsula el cálculo de saldo y creación de `MovimientoCaja`
- **`ticket_ruta.py`**: Router FastAPI bajo el prefijo `/tickets` (interfaz web)
- **`mobile_api_ruta.py`**: Router FastAPI bajo el prefijo `/api/mobile` (app móvil)
- **`mobile_ruta.py`**: Router obsoleto bajo el prefijo `/mobile/v1` — dead code
- **`dependencias.py`**: Módulo con las dependencias de autenticación (`requerir_password_pdf`, `requerir_password_admin`)
- **`PDF_PASSWORD`**: Variable de entorno que debe proveer la contraseña del PDF; actualmente tiene fallback hardcodeado a `"1234"`
- **`vehiculo_id`**: FK en el modelo `Ticket` que apunta al modelo `Vehiculo` donde residen `nombre_propietario` y `telefono_propietario`
- **`conftest.py`**: Archivo de configuración de pytest que establece variables de entorno antes de importar la app; actualmente hardcodea `"1234"` para `PDF_PASSWORD` y `ADMIN_PASSWORD`
- **`slowapi`**: Librería de rate limiting para FastAPI/Starlette declarada en `requirements.txt` pero no configurada ni aplicada en ningún endpoint
- **`obtener_resumen_ticket`**: Endpoint `GET /api/mobile/tickets/{id}/resumen` que ejecuta 6 queries separadas en lugar de una query con agregaciones
- **`mobile_schema.py`**: Módulo a crear en `app/esquemas/` que centralizará los 14 schemas Pydantic actualmente definidos inline en `mobile_api_ruta.py`

---

## Bug Details

### Bug Condition

Cinco condiciones independientes activan los defectos:

**Formal Specification:**
```
FUNCTION isBugCondition(input)
  INPUT: input de tipo BugInput { tipo, contexto }
  OUTPUT: boolean

  IF input.tipo == "FINALIZACION"
    RETURN ticket_ruta.finalizar_ticket Y mobile_api_ruta.actualizar_estado_mobile
           tienen lógica de saldo/MovimientoCaja copiada sin función compartida

  IF input.tipo == "ROUTER_REGISTRO"
    RETURN mobile_ruta está registrado en main.py
           Y ningún cliente consume /mobile/v1/*

  IF input.tipo == "REQUEST_SIN_AUTH"
    RETURN input.path STARTS_WITH "/tickets" OR "/api/mobile/tickets"
           AND NOT "X-PDF-Password" IN input.headers
           AND NOT "X-Admin-Password" IN input.headers

  IF input.tipo == "PDF_PASSWORD_ENV"
    RETURN "PDF_PASSWORD" NOT IN os.environ
           AND sistema usa "1234" como fallback

  IF input.tipo == "PDF_GENERACION"
    RETURN ticket.nombre_propietario evaluado con hasattr()
           AND "nombre_propietario" NOT IN Ticket.__table__.columns

  IF input.tipo == "TEST_PASSWORDS_HARDCODED"
    RETURN "PDF_PASSWORD" hardcodeado como "1234" en tests/conftest.py
           OR "ADMIN_PASSWORD" hardcodeado como "1234" en tests/conftest.py

  IF input.tipo == "RATE_LIMITING_AUSENTE"
    RETURN "slowapi" IN requirements.txt
           AND slowapi NOT configurado en main.py
           AND ningún endpoint tiene límite de tasa aplicado

  IF input.tipo == "N_PLUS_1_RESUMEN"
    RETURN endpoint == "GET /api/mobile/tickets/{id}/resumen"
           AND queries_ejecutadas >= 6
           AND NO usa func.count() NI func.sum() en query única

  IF input.tipo == "SCHEMAS_INLINE"
    RETURN schemas Pydantic definidos en mobile_api_ruta.py
           AND NOT EXISTS "app/esquemas/mobile_schema.py"

  RETURN False
END FUNCTION
```

### Examples

- **Lógica duplicada**: Se modifica el cálculo de saldo en `ticket_ruta.py` pero se olvida actualizar `mobile_api_ruta.py` → los tickets finalizados desde la app móvil calculan saldo incorrecto
- **Dead code**: `GET /mobile/v1/health` responde 200 aunque ningún cliente lo usa; genera confusión en la documentación OpenAPI
- **Sin autenticación**: `curl http://localhost:8000/tickets` devuelve todos los tickets sin ninguna credencial
- **Password hardcodeado**: Con `PDF_PASSWORD` no definida, cualquiera que lea el código fuente conoce la contraseña (`"1234"`)
- **PDF vacío**: `GET /tickets/42/pdf` genera un PDF donde "Propietario:" y "Teléfono:" aparecen en blanco porque `hasattr(ticket, 'nombre_propietario')` retorna `False`
- **Passwords en tests**: `tests/conftest.py` contiene `os.environ.setdefault("PDF_PASSWORD", "1234")` — cualquiera que clone el repo conoce la contraseña de producción
- **Rate limiting ausente**: `curl -X POST http://localhost:8000/api/mobile/tickets/1/estado` puede ejecutarse miles de veces por segundo sin ningún límite
- **N+1 en resumen**: `GET /api/mobile/tickets/1/resumen` con 100 compras y 50 cobros ejecuta 6 queries en lugar de 1, degradando el rendimiento con carga alta
- **Schemas inline**: `from app.rutas.mobile_api_ruta import TicketListResponse` funciona pero viola la separación de responsabilidades; un segundo router que necesite `TicketListResponse` tendría que importarlo desde el router en lugar del módulo de esquemas

---

## Expected Behavior

### Preservation Requirements

**Unchanged Behaviors:**
- Un ticket finalizado con `total_servicio` definido DEBE seguir calculando `saldo_pendiente = total_servicio - anticipo_recibido - total_cobros` (mínimo 0)
- Un ticket finalizado DEBE seguir creando un `MovimientoCaja` de tipo `INGRESO_FINAL` con valor `total_servicio - anticipo_recibido`
- Intentar finalizar un ticket sin `total_servicio` DEBE seguir retornando `400 Bad Request`
- Un cliente autenticado correctamente DEBE seguir recibiendo respuestas normales de los endpoints de tickets
- Los endpoints de economía, vehículos, citas y seguridad NO deben verse afectados
- Cuando `PDF_PASSWORD` está definida en el entorno, DEBE seguir usándose ese valor para validar `X-PDF-Password`
- El PDF DEBE seguir mostrando `nombre_propietario` y `telefono_propietario` cuando el vehículo asociado los tiene

**Scope:**
Todos los inputs que NO activen ninguna de las cinco condiciones del bug deben comportarse exactamente igual que antes del fix. Esto incluye:
- Peticiones autenticadas a `/tickets` y `/api/mobile/tickets`
- Generación de PDF cuando el vehículo existe y tiene datos del propietario
- Arranque del sistema cuando `PDF_PASSWORD` está definida
- Todos los demás routers (`/vehiculos`, `/economia`, `/citas`, `/seguridad`, `/upload`)

---

## Hypothesized Root Cause

1. **Lógica de finalización copiada manualmente**: Al crear `mobile_api_ruta.py`, la lógica de `POST /tickets/{id}/finalizar` fue copiada dentro del bloque `if data.estado == "FINALIZADO"` de `PATCH /api/mobile/tickets/{id}/estado` sin extraerla a una función compartida. No existe un módulo de servicios (`app/servicios/`) con lógica de negocio reutilizable.

2. **Router registrado sin verificar uso**: `mobile_ruta.py` fue creado como prototipo inicial de la API móvil y luego reemplazado por `mobile_api_ruta.py`, pero su registro en `main.py` nunca fue eliminado.

3. **Dependencias de autenticación no aplicadas a nivel de router**: `dependencias.py` define `requerir_password_pdf` y `requerir_password_admin`, pero los routers `/tickets` y `/api/mobile` no incluyen ninguna dependencia de autenticación en su `APIRouter(...)` ni en los endpoints individuales.

4. **Fallback inseguro en `os.getenv`**: `dependencias.py` usa `os.getenv("PDF_PASSWORD", "1234")` — el segundo argumento de `getenv` actúa como valor por defecto, exponiendo la contraseña en el código fuente y permitiendo que el sistema arranque sin configuración de seguridad.

5. **`hasattr()` sobre modelo SQLAlchemy**: En `ticket_ruta.py`, el endpoint `GET /{ticket_id}/pdf` construye `ticket_dict` usando `hasattr(ticket, 'nombre_propietario')`. El modelo `Ticket` no tiene esas columnas (residen en `Vehiculo`), por lo que `hasattr` retorna `False` y los campos quedan vacíos. La solución correcta es consultar el `Vehiculo` por `ticket.vehiculo_id`, como ya hace correctamente `mobile_api_ruta.py`.

6. **Passwords hardcodeadas en `conftest.py`**: `tests/conftest.py` usa `os.environ.setdefault("PDF_PASSWORD", "1234")` y `os.environ.setdefault("ADMIN_PASSWORD", "1234")`. Esto expone las contraseñas de producción en el código fuente. La solución es leer esos valores desde un archivo `.env.test` (en `.gitignore`) o desde variables de entorno del sistema, con un fallback documentado solo para CI.

7. **`slowapi` declarado pero no configurado**: `requirements.txt` incluye `slowapi` pero `app/main.py` no crea el `Limiter`, no registra el handler de `RateLimitExceeded` y ningún endpoint tiene el decorador `@limiter.limit(...)`. La dependencia instalada sin uso es dead weight y deja los endpoints sensibles expuestos a abuso.

8. **N+1 queries en `obtener_resumen_ticket`**: La función ejecuta 6 queries independientes: 4 `COUNT` separados (procesos, repuestos, fotos, compras) y 2 cargas completas de registros para sumar valores (compras y cobros). Con muchos tickets activos y llamadas frecuentes desde la app móvil, esto degrada el rendimiento. La solución es consolidar en una sola query con `func.count()` y `func.sum()` usando `outerjoin` o subqueries.

9. **Schemas Pydantic inline en el router**: Los 14 schemas de `mobile_api_ruta.py` están definidos en el mismo archivo que los endpoints. Esto viola la separación de responsabilidades: el router debería solo definir rutas, no tipos de datos. Además impide reutilizar los schemas desde otros módulos sin importar el router completo.

---

## Correctness Properties

Property 1: Bug Condition — Lógica de finalización unificada

_For any_ ticket con `total_servicio` definido que sea finalizado, ya sea desde `POST /tickets/{id}/finalizar` o desde `PATCH /api/mobile/tickets/{id}/estado` con `estado=FINALIZADO`, la función `_finalizar_ticket` SHALL calcular `saldo_pendiente`, crear el `MovimientoCaja` de tipo `INGRESO_FINAL` y actualizar el estado del ticket de forma idéntica en ambos casos.

**Validates: Requirements 2.1, 2.2**

Property 2: Bug Condition — Endpoints de tickets requieren autenticación

_For any_ petición HTTP a cualquier endpoint bajo `/tickets` o `/api/mobile/tickets` que NO incluya la cabecera de autenticación correcta, el sistema SHALL retornar `401 Unauthorized` sin procesar la petición.

**Validates: Requirements 2.4, 2.5**

Property 3: Bug Condition — PDF incluye datos del propietario

_For any_ ticket con `vehiculo_id` válido cuyo vehículo asociado tenga `nombre_propietario` y/o `telefono_propietario`, el PDF generado por `GET /tickets/{id}/pdf` SHALL incluir esos valores en la sección "INFORMACIÓN DEL VEHÍCULO Y TICKET".

**Validates: Requirements 2.7, 3.4**

Property 4: Preservation — Cálculo de saldo y MovimientoCaja sin regresión

_For any_ ticket finalizado correctamente (con `total_servicio` definido), la función `_finalizar_ticket` SHALL CONTINUE TO calcular `saldo_pendiente = total_servicio - anticipo_recibido - total_cobros` (mínimo 0) y crear un `MovimientoCaja` de tipo `INGRESO_FINAL` con valor `total_servicio - anticipo_recibido`, preservando el comportamiento financiero existente.

**Validates: Requirements 3.1, 3.2, 3.3**

Property 5: Preservation — Clientes autenticados no se ven afectados

_For any_ petición a `/tickets` o `/api/mobile/tickets` que incluya la cabecera de autenticación correcta, el sistema SHALL CONTINUE TO procesar la petición y retornar la respuesta esperada, sin cambios en el comportamiento funcional.

**Validates: Requirements 3.5, 3.6**

---

Property 6: Bug Condition — Tests no exponen contraseñas de producción

_For any_ ejecución de la suite de tests, el sistema SHALL leer `PDF_PASSWORD` y `ADMIN_PASSWORD` desde variables de entorno del sistema o desde `.env.test` (excluido de git), y SHALL NOT tener esos valores hardcodeados en el código fuente del repositorio.

**Validates: Requirements 1.8, 2.8**

Property 7: Bug Condition — Rate limiting activo en endpoints sensibles

_For any_ cliente que supere el límite de peticiones configurado en los endpoints de autenticación o generación de PDF, el sistema SHALL retornar `429 Too Many Requests` sin procesar la petición.

**Validates: Requirements 1.9, 2.9**

Property 8: Bug Condition — Query consolidada en resumen de ticket

_For any_ llamada a `GET /api/mobile/tickets/{id}/resumen`, el sistema SHALL ejecutar como máximo 2 queries a la base de datos (una para el ticket y una para los agregados), retornando los mismos valores que la implementación original con 6 queries.

**Validates: Requirements 1.10, 2.10, 3.10**

Property 9: Bug Condition — Schemas en módulo dedicado

_For any_ importación de schemas del dominio mobile, el sistema SHALL resolverlos desde `app/esquemas/mobile_schema.py`, y el router `mobile_api_ruta.py` SHALL importarlos desde ese módulo en lugar de definirlos inline.

**Validates: Requirements 1.11, 2.11, 3.11**

Property 10: Preservation — Resumen retorna valores idénticos tras consolidación

_For any_ ticket con procesos, repuestos, fotos, compras y cobros existentes, la query consolidada SHALL CONTINUE TO retornar exactamente los mismos contadores y sumas financieras que la implementación original con queries separadas.

**Validates: Requirements 3.10**

---

## Fix Implementation

### Changes Required

**Archivo 1**: `app/servicios/ticket_service.py` *(nuevo)*

**Función**: `_finalizar_ticket(ticket, db)`

**Cambios específicos**:
1. Crear el directorio/módulo `app/servicios/` con `__init__.py`
2. Extraer la lógica de finalización a esta función compartida:
   - Validar que `ticket.total_servicio` esté definido (raise HTTPException 400 si no)
   - Calcular `total_cobros` sumando `TicketCobro` del ticket
   - Calcular `saldo = total_servicio - anticipo_recibido - total_cobros` (mínimo 0)
   - Asignar `ticket.saldo_pendiente`, `ticket.estado = "FINALIZADO"`, `ticket.fecha_cierre`
   - Crear `MovimientoCaja` de tipo `INGRESO_FINAL` si `valor_ingreso > 0`
   - Hacer `db.add(movimiento)` pero NO `db.commit()` (el commit lo hace el caller)

---

**Archivo 2**: `app/rutas/ticket_ruta.py`

**Función**: `finalizar_ticket`

**Cambios específicos**:
1. Importar `_finalizar_ticket` desde `app.servicios.ticket_service`
2. Reemplazar la lógica inline de cálculo de saldo y creación de movimiento por una llamada a `_finalizar_ticket(ticket, db)`
3. Mantener el `db.commit()` y `db.refresh(ticket)` en el endpoint

---

**Archivo 3**: `app/rutas/mobile_api_ruta.py`

**Función**: `actualizar_estado_mobile`

**Cambios específicos**:
1. Importar `_finalizar_ticket` desde `app.servicios.ticket_service`
2. Reemplazar el bloque `if data.estado == "FINALIZADO" and estado_anterior != "FINALIZADO":` con una llamada a `_finalizar_ticket(ticket, db)`
3. Agregar la dependencia de autenticación al `APIRouter` o a los endpoints individuales de `/tickets`
4. Mantener el `db.commit()` y `db.refresh(ticket)` en el endpoint

---

**Archivo 4**: `app/main.py`

**Cambios específicos**:
1. Eliminar el import de `mobile_ruta` de la línea de imports
2. Eliminar `app.include_router(mobile_ruta.router)`

---

**Archivo 5**: `app/seguridad/dependencias.py`

**Función**: `requerir_password_pdf`

**Cambios específicos**:
1. Reemplazar `os.getenv("PDF_PASSWORD", "1234")` por lógica que lance `RuntimeError` si `PDF_PASSWORD` no está definida:
   ```python
   password_esperada = os.environ.get("PDF_PASSWORD")
   if not password_esperada:
       raise RuntimeError("La variable de entorno PDF_PASSWORD es obligatoria")
   ```
2. Aplicar el mismo patrón a `requerir_password_admin` para `ADMIN_PASSWORD`

---

**Archivo 6**: `app/rutas/ticket_ruta.py`

**Función**: `generar_pdf_cliente`

**Cambios específicos**:
1. Importar `Vehiculo` desde `app.modelos.vehiculo`
2. Consultar el vehículo: `vehiculo = db.query(Vehiculo).filter(Vehiculo.id == ticket.vehiculo_id).first()`
3. Reemplazar:
   ```python
   'nombre_propietario': ticket.nombre_propietario if hasattr(ticket, 'nombre_propietario') else None,
   'telefono_propietario': ticket.telefono_propietario if hasattr(ticket, 'telefono_propietario') else None,
   ```
   por:
   ```python
   'nombre_propietario': vehiculo.nombre_propietario if vehiculo else None,
   'telefono_propietario': vehiculo.telefono_propietario if vehiculo else None,
   ```

---

**Archivo 7**: `app/rutas/ticket_ruta.py` y `app/rutas/mobile_api_ruta.py`

**Cambios específicos**:
1. Agregar `dependencies=[Depends(requerir_password_admin)]` al `APIRouter(...)` de `ticket_ruta.py`
2. Agregar `dependencies=[Depends(requerir_password_admin)]` al `APIRouter(...)` de `mobile_api_ruta.py`
3. Importar `requerir_password_admin` desde `app.seguridad.dependencias`

---

**Archivo 8**: `tests/conftest.py`

**Cambios específicos**:
1. Crear (o verificar existencia de) `.env.test` con `PDF_PASSWORD` y `ADMIN_PASSWORD` reales, y agregar `.env.test` a `.gitignore`
2. Reemplazar los `os.environ.setdefault("PDF_PASSWORD", "1234")` y `os.environ.setdefault("ADMIN_PASSWORD", "1234")` por carga desde `.env.test` usando `python-dotenv`:
   ```python
   from dotenv import load_dotenv
   load_dotenv(".env.test", override=False)
   ```
3. Agregar fallback explícito solo para CI con comentario documentando el motivo:
   ```python
   # Fallback para CI donde .env.test no existe — usar variables de entorno del sistema
   os.environ.setdefault("PDF_PASSWORD", os.getenv("CI_PDF_PASSWORD", ""))
   os.environ.setdefault("ADMIN_PASSWORD", os.getenv("CI_ADMIN_PASSWORD", ""))
   ```

---

**Archivo 9**: `app/main.py` y endpoints sensibles

**Cambios específicos**:
1. Importar `slowapi`: `from slowapi import Limiter, _rate_limit_exceeded_handler` y `from slowapi.util import get_remote_address` y `from slowapi.errors import RateLimitExceeded`
2. Crear el limiter: `limiter = Limiter(key_func=get_remote_address)`
3. Registrar el limiter en el estado de la app: `app.state.limiter = limiter`
4. Registrar el handler de error: `app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)`
5. Aplicar `@limiter.limit("10/minute")` a los endpoints de autenticación (`POST /seguridad/login` o equivalente) y `@limiter.limit("20/minute")` a los endpoints de generación de PDF (`GET /tickets/{id}/pdf`)

---

**Archivo 10**: `app/esquemas/mobile_schema.py` *(nuevo)*

**Cambios específicos**:
1. Crear `app/esquemas/mobile_schema.py` con los 14 schemas actualmente en `mobile_api_ruta.py`: `TicketListResponse`, `TicketDetailResponse`, `ProcesoResponse`, `RepuestoResponse`, `FotoResponse`, `ProcesoCreate`, `RepuestoCreate`, `ActualizarEstadoTicket`, `CompraResponse`, `CompraCreate`, `CobroResponse`, `CobroCreate`, `ActualizarFinanzasData`, `EntregarTicketData`
2. En `app/rutas/mobile_api_ruta.py`: eliminar las definiciones inline de los 14 schemas y reemplazarlas por un import: `from app.esquemas.mobile_schema import (...)`

---

**Archivo 11**: `app/rutas/mobile_api_ruta.py`

**Función**: `obtener_resumen_ticket`

**Cambios específicos**:
1. Importar `func` desde `sqlalchemy`: `from sqlalchemy import func`
2. Reemplazar las 6 queries separadas por una query consolidada usando `func.count()` y `func.sum()`:
   ```python
   from sqlalchemy import func
   
   stats = db.query(
       func.count(TicketProceso.id).label("total_procesos"),
       func.count(TicketRepuesto.id).label("total_repuestos"),
       func.count(TicketCompra.id).label("total_compras"),
   ).filter(...).one()
   
   # Fotos (excluye tipo PROCESO) y sumas financieras en queries separadas mínimas
   total_fotos = db.query(func.count(TicketFoto.id)).filter(
       TicketFoto.ticket_id == ticket_id,
       TicketFoto.tipo != "PROCESO"
   ).scalar()
   
   sumas = db.query(
       func.coalesce(func.sum(TicketCompra.valor), 0).label("total_egresos"),
   ).filter(TicketCompra.ticket_id == ticket_id).one()
   
   total_cobros = db.query(
       func.coalesce(func.sum(TicketCobro.valor), 0)
   ).filter(TicketCobro.ticket_id == ticket_id).scalar()
   ```
3. Mantener exactamente la misma estructura de respuesta JSON

---

## Testing Strategy

### Validation Approach

La estrategia sigue dos fases: primero ejecutar tests exploratorios sobre el código SIN fix para confirmar los root causes, luego verificar el fix y la preservación.

### Exploratory Bug Condition Checking

**Goal**: Confirmar los root causes antes de implementar el fix. Si los tests no fallan como se espera, revisar la hipótesis.

**Test Plan**: Escribir tests unitarios/de integración que ejerciten cada condición del bug sobre el código actual (sin fix) y observar los fallos.

**Test Cases**:
1. **Duplicación de lógica**: Llamar a `finalizar_ticket` desde `ticket_ruta` y a `actualizar_estado_mobile` con `FINALIZADO` desde `mobile_api_ruta` con el mismo ticket base y verificar que producen el mismo resultado — fallará si divergen
2. **Dead code activo**: Hacer `GET /mobile/v1/health` y verificar que retorna 200 (confirma que el router está registrado)
3. **Sin autenticación**: Hacer `GET /tickets` sin cabecera `X-Admin-Password` y verificar que retorna 200 en lugar de 401 (confirma la ausencia de auth)
4. **Password fallback**: Con `PDF_PASSWORD` no definida, llamar a `requerir_password_pdf` con password `"1234"` y verificar que acepta la petición (confirma el fallback inseguro)
5. **PDF sin propietario**: Generar PDF de un ticket con vehículo que tiene `nombre_propietario` y verificar que el `ticket_dict` tiene `None` en ese campo (confirma el bug de `hasattr`)

**Expected Counterexamples**:
- Tests 3 y 4 confirman exposición de seguridad
- Test 5 confirma que `hasattr(ticket, 'nombre_propietario')` retorna `False`

### Fix Checking

**Goal**: Verificar que para todos los inputs donde la condición del bug se cumple, la función corregida produce el comportamiento esperado.

**Pseudocode:**
```
FOR ALL input WHERE isBugCondition(input) DO
  result := fixed_function(input)
  ASSERT expectedBehavior(result)
END FOR
```

### Preservation Checking

**Goal**: Verificar que para todos los inputs donde la condición del bug NO se cumple, el comportamiento es idéntico al original.

**Pseudocode:**
```
FOR ALL input WHERE NOT isBugCondition(input) DO
  ASSERT original_function(input) == fixed_function(input)
END FOR
```

**Testing Approach**: Se recomienda property-based testing para la preservación del cálculo financiero porque:
- Genera automáticamente muchas combinaciones de `total_servicio`, `anticipo_recibido` y `cobros`
- Detecta edge cases (saldo negativo, anticipo mayor que total, etc.)
- Garantiza que la función compartida produce el mismo resultado que las implementaciones originales

**Test Cases**:
1. **Preservación financiera**: Para cualquier combinación válida de `total_servicio`, `anticipo_recibido` y lista de cobros, `_finalizar_ticket` debe producir el mismo `saldo_pendiente` que la lógica original de `ticket_ruta`
2. **Preservación de autenticación**: Peticiones con `X-Admin-Password` correcta siguen recibiendo respuestas 200
3. **Preservación de otros routers**: `GET /vehiculos`, `GET /economia`, etc. siguen funcionando sin cambios

### Unit Tests

- Test de `_finalizar_ticket` con `total_servicio` definido → verifica saldo, estado y movimiento de caja
- Test de `_finalizar_ticket` sin `total_servicio` → verifica que lanza `HTTPException(400)`
- Test de `requerir_password_pdf` sin `PDF_PASSWORD` en entorno → verifica `RuntimeError`
- Test de `requerir_password_pdf` con `PDF_PASSWORD` definida → verifica que acepta la contraseña correcta y rechaza la incorrecta
- Test de `generar_pdf_cliente` con vehículo que tiene propietario → verifica que `ticket_dict` contiene los datos correctos

### Property-Based Tests

- Generar combinaciones aleatorias de `(total_servicio, anticipo_recibido, cobros[])` y verificar que `saldo_pendiente = max(0, total_servicio - anticipo - sum(cobros))` (Property 4)
- Generar peticiones aleatorias sin cabecera de auth a `/tickets/*` y verificar que todas retornan 401 (Property 2)
- Generar tickets con vehículos aleatorios y verificar que el PDF siempre incluye los datos del propietario cuando existen (Property 3)
- Generar tickets con cantidades aleatorias de procesos, repuestos, compras y cobros y verificar que la query consolidada retorna los mismos valores que las queries separadas (Property 10)

### Integration Tests

- Test end-to-end: crear ticket → agregar cobros → finalizar desde `/tickets/{id}/finalizar` → verificar `saldo_pendiente` y `MovimientoCaja`
- Test end-to-end: crear ticket → finalizar desde `/api/mobile/tickets/{id}/estado` → verificar que el resultado es idéntico al anterior
- Test de arranque: iniciar la app sin `PDF_PASSWORD` → verificar que falla con error de configuración
- Test de PDF completo: crear ticket con vehículo con propietario → generar PDF → verificar que contiene nombre y teléfono
- Test de rate limiting: enviar más de 10 peticiones por minuto al endpoint de autenticación → verificar que la petición 11 retorna 429
- Test de resumen consolidado: crear ticket con N procesos, M compras y K cobros → llamar a `/resumen` → verificar contadores y sumas correctos
- Test de schemas: importar `TicketListResponse` desde `app.esquemas.mobile_schema` → verificar que funciona sin importar el router
