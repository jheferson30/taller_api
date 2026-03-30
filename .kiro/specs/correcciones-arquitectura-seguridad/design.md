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
           AND NOT "X-Admin-Password"rs

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
obile_schema.py"

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
- **N+1 en resumen**: `GET /api/mobile/tickets/1/resumen` con 100 compras y 50 cobros ejecuta 6 queries en lugar de 1-2, degradando el rendimiento con carga alta
- **Schemas inline**: `from app.rutas.mobile_api_ruta import TicketListResponse` funciona pero viola la separación de responsabilidades; un segundo router que necesite uemas

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
- Los tests existentes DEBEN seguir pasando cuando `.env.test` está presente con las variables correctas
- Peticiones dentro del límite de tasa DEBEN seguir procesándose normalmente
- `GET /api/mobile/tickets/{id}/resumen` DEBE retornar exactamente los mismos valores tras la consolidación de queries
- Los schemas del router mobile DEBEN mantener los mismos campos y validaciones tras ser movidos a `mobile_schema.py`

---

## Hypothesized Root Cause

1. **Lógica de finalización copiada manualmente**: Al crear `mobile_api_ruta.py`, la lóga a una función compartida.

2. **Router registrado sin verificar uso**: `mobile_ruta.py` fue creado como prototipo inicial y luego reemplazado por `mobile_api_ruta.py`, pero su registro en `main.py` nunca fue eliminado.

3. **Dependencias de autenticación no aplicadas a nivel de router**: `dependencias.py` define `requerir_password_pdf` y `requerir_password_admin`, pero los routers `/tickets` y `/api/mobile` no las incluyen.

4. **Fallback inseguro en `os.getenv`**: `dependencias.py` usa `os.getenv("PDF_PASSWORD", "1234")` — el segundo argumento actúa como valor por defecto, exponiendo la contraseña en el código fuente.

5. **`hasattr()` sobre modelo SQLAlchemy**: En `ticket_ruta.py`, el endpoint `GET /{ticket_id}/pdf` usa `hasattr(ticket, 'nombre_propietario')`. El modelo `Ticket` no tiene esas columnas (residen en `Vehiculo`), por lo que `hasattr` retorna `False`.

6. **Passwords hardcodeadas en `conftest.py`**: `tests/conftest.py` usa `os.environ.setdefault("PDF_PASSWORD", "1234")` y `os.environ.setdefault("ADMIN_PASSWORD", "1234")`. Esto expone las contraseñas de producción en el código fuente. La solución es leer esos valores desde un archivo `.env.test` (en `.gitignore`) o desde variables de entorno del sistema.

7. **`slowapi` declarado pero no configurado**: `requirements.txt` incluye `slowapi` pero `app/main.py` no crea el `Limiter`, no registra el handler de `RateLimitExceeded` y ningún endpoint tiene el decorador `@limiter.limit(...)`.

8. **N+1 queries en `obtener_resumen_ticket`**: La función ejecuta 6 queries independientes: 4 `COUNT` separados y 2 cargas completas de registros para sumar valores. La solución es consolidar con `func.count()` y `func.sum()`.

9. **Schemas Pydantic inline en el router**: Los 14 schemas de `mobile_api_ruta.py` están definidos en el mismo archivo que los endpoints, violando la separación de responsabilidades e impidiendo reutilización.

---

## Correctness Properties

Property 1: Bug Condition — Lógica de finalización unificada

_Foizado, ya sea desde `POST /tickets/{id}/finalizar` o desde `PATCH /api/mobile/tickets/{id}/estado` con `estado=FINALIZADO`, la función `_finalizar_ticket` SHALL calcular `saldo_pendiente`, crear el `MovimientoCaja` de tipo `INGRESO_FINAL` y actualizar el estado del ticket de forma idéntica en ambos casos.

**Validates: Requirements 2.1, 2.2**

Property 2: Bug Condition — Endpoints de tickets requieren autenticación

_For any_ petición HTTP a cualquier endpoint bajo `/tickets` o `/api/mobile/tickets` que NO incluya la cabecera de autenticación correcta, el sistema SHALL retornar `401 Unauthorized` sin procesar la petición.

**Validates: Requirements 2.4, 2.5**

Property 3: Bug Condition — PDF incluye datos del propietario

_For any_ ticket con `vehiculo_id` válido cuyo vehículo asociado tenga `nombre_propietario` y/o `telefono_propietario`, el PDF generado por `GET /tickets/{id}/pdf` SHALL incluir esos valores en la sección "INFORMACIÓN DEL VEHÍCULO Y TICKET".

**Validates: Requirements 2.7, 3.4**

Property 4: Preservation — Cálculo de saldo y MovimientoCaja sin regresión

_For any_ ticket finalizado correctamente (con `total_servicio` definido), la función `_finalizar_ticket` SHALL CONTINUE TO calcular `saldo_pendiente = total_servicio - anticipo_recibido - total_cobros` (mínimo 0) y crear un `MovimientoCaja` de tipo `INGRESO_FINAL` con valor `total_servicio - anticipo_recibido`.

**Validates: Requirements 3.1, 3.2, 3.3**

Property 5: Preservation — Clientes autenticados no se ven afectados

_For any_ petición a `/tickets` o `/api/mobile/tickets` que incluya la cabecera de autenticación correcta, el sistema SHALL CONTINUE TO procesar la petición y retornar la respuesta esperada.

**Validates: Requirements 3.5, 3.6**

Property 6: Bug Condition — Tests no exponen contraseñas de producción

_For any_ ejecución de la suite de tests, el sistema SHALL leer `PDF_PASSWORD` y `ADMIN_PASSWORD` desde variables de entorno del sistema o desde `.env.test` (excluido de git), y SHALL NOT tener esos valores hardcodeados en el código f repositorio.

**Validates: Requirements 1.8, 2.8**

Property 7: Bug Condition — Rate limiting activo en endpoints sensibles

_For any_ cliente que supere el límite de peticiones configurado en los endpoints de autenticación o generación de PDF, el sistema SHALL retornar `429 Too Many Requests` sin procesar la petición.

**Validates: Requirements 1.9, 2.9**

Property 8: Bug Condition — Query consolidada en resumen de ticket

_For any_ llamada a `GET /api/mobile/tickets/{id}/resumen`, el sistema máximo 2 queries a la base de datos, retornando los mismos valores que la implementación original con 6 queries.

**Validates: Requirements 1.10, 2.10, 3.10**

Property 9: Bug Condition — Schemas en módulo dedicado

_For any_ importación de schemas del dominio mobile, el sistema SHALL resolverlos desde `app/esquemas/mobile_schema.py`, y el router `mobile_api_ruta.py` SHALL importarlos desde ese módulo en lugar de definirlos inline.

**Validates: Requirements 1.11, 2.11, 3.11**

Property 10: Preservation — Resumen retorna valores idénticos tras consolidación

_For any_ ticket con procesos, repuestos, fotos, compras y cobros existentes, la query consolidada SHALL CONTINUE TO retornar exactamente los mismos contadores y sumas financieras que la implementación original.

**Validates: Requirements 3.10**

---

## Fix Implementation

### Changes Required

**Archivo 1**: `app/servicios/ticket_service.py` *(ya implementado)*

**Archivo 2**: `app/rutas/ticket_ruta.py` — `finalizar_ticket` *(ya implementado)*

**Archivo 3**: `app/rutas/mobile_api_ruta.py` — `actualizar_estado_mobile` *(ya implementado)*

**Archivo 4**: `app/main.py` — eliminar router dead code *(ya implementado)*

**Archivo 5**: `app/seguridad/dependencias.py` — `requerir_password_pdf` *(ya implementado)*

**Archivo 6**: `app/rutas/ticket_ruta.py` — `generar_pdf_cliente` *(ya implementado)*

**Archivo 7**: `app/rutas/ticket_ruta.py` y `app/rutas/mobile_api_ruta.py` — autenticación *(ya implementado)*

---

**Archivo 8**: `tests/conftest.py`

**Cambios específicos**:
1. Crear `tests/.env.test` (o `.env.test` en la raíz) con `PDF_PASSWORD` y `ADMIN_PASSWORD` con valores reales de test, y agregar `.env.test` a `.gitignore`
2. Crear `tests/.env.test.example` con valores placeholder como documentación
3. En `tests/conftest.py`: agregar `from dotenv import load_dotenv` y llamar a `load_dotenv(".env.test", override=False)` antes de los `setdefault`
4. Reemplazar los valores hardcodeados `"1234"` por lectura desde el entorno sin hardcodear

---

**Archivo 9**: `app/main.py` y s sensibles

**Cambios específicos**:
1. Importar `Limiter`, `_rate_limit_exceeded_handler` desde `slowapi`, `get_remote_address` desde `slowapi.util`, `RateLimitExceeded` desde `slowapi.errors`
2. Crear instancia: `limiter = Limiter(key_func=get_remote_address)`
3. Registrar en el estado de la app: `app.state.limiter = limiter`
4. Registrar el handler: `app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)`
5. Aplicar `@limiter.limit("20/minute")` al endpoint `GET /tickets/{id}/pdf`
@limiter.limit("30/minute")` a `PATCH /api/mobile/tickets/{id}/estado`

---

**Archivo 10**: `app/esquemas/mobile_schema.py` *(nuevo)*

**Cambios específicos**:
1. Crear `app/esquemas/mobile_schema.py` con los 14 schemas actualmente en `mobile_api_ruta.py`
2. En `app/rutas/mobile_api_ruta.py`: eliminar las definiciones inline y reemplazar por `from app.esquemas.mobile_schema import (...)`

---

**Archivo 11**: `app/rutas/mobile_api_ruta.py` — `obtener_resumen_ticket`

**Cambios específicos**:
1. Importar `func` desde `sqlalchemy`
2. Reemplazar las 6 queries separadas por queries con `func.count()` y `func.sum()`/`func.coalesce()`:
   - Una query para contar procesos, repuestos y compras
   - Una query para fotos (con filtro `tipo != "PROCESO"`)
   - Una query para sumar egresos y cobros
3. Mantener exactamente la misma estructura de respuesta JSON

---

## Testing Strategy

### Validation Approach

La estrategia sigue dos fases: primero ejecutar testsuses, luego verificar el fix y la preservación.

### Property-Based Tests

- Generar combinaciones aleatorias de `(total_servicio, anticipo_recibido, cobros[])` y verificar que `saldo_pendiente = max(0, total_servicio - anticipo - sum(cobros))` (Property 4)
- Generar peticiones aleatorias sin cabecera de auth a `/tickets/*` y verificar que todas retornan 401 (Property 2)
- Generar tickets con vehículos aleatorios y verificar que el PDF siempre incluye los datos del propietario cuando existen (Property 3)
erar tickets con cantidades aleatorias de procesos, repuestos, compras y cobros y verificar que la query consolidada retorna los mismos valores que las queries separadas (Property 10)

### Integration Tests

- Test de rate limiting: enviar más de 20 peticiones por minuto al endpoint de PDF → verificar que la petición 21 retorna 429
- Test de resumen consolidado: crear ticket con N procesos, M compras y K cobros → llamar a `/resumen` → verificar contadores y sumas correctos
- Test de schemas: importar `TicketListResponse` desde `app.esquemas.mobile_schema` → verificar que funciona sin importar el router
- Test de conftest: verificar que `.env.test` no aparece en `git status`
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
- **`_finalizar_ticket(ticket, db)`**: Función compartida que encapsula el cálculo de saldo y creación de `MovimientoCaja`
- **`ticket_ruta.py`**: Router FastAPI bajo el prefijo `/tickets` (interfaz web)
- **`mobile_api_ruta.py`**: Router FastAPI bajo el prefijo `/api/mobile` (app móvil)
- **`mobile_ruta.py`**: Router obsoleto bajo el prefijo `/mobile/v1` — dead code
- **`dependencias.py`**: Módulo con las dependencias de autenticación (`requerir_password_pdf`, `requerir_password_admin`)
- **`PDF_PASSWORD`**: Variable de entorno que debe proveer la contraseña del PDF
- **`vehiculo_id`**: FK en el modelo `Ticket` que apunta al modelo `Vehiculo`
- **`conftest.py`**: Archivo de configuración de pytest; actualmente hardcodea `"1234"` para `PDF_PASSWORD` y `ADMIN_PASSWORD`
- **`slowapi`**: Librería de rate limiting declarada en `requirements.txt` pero no configurada ni aplicada
- **`obtener_resumen_ticket`**: Endpoint `GET /api/mobile/tickets/{id}/resumen` que ejecuta 6 queries separadas
- **`mobile_schema.py`**: Módulo a crear en `app/esquemas/` que centralizará los 14 schemas Pydantic actualmente inline en `mobile_api_ruta.py`

---

## Bug Details

### Bug Condition

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

- **Lógica duplicada**: Se modifica el cálculo de saldo en `ticket_ruta.py` pero se olvida actualizar `mobile_api_ruta.py` → saldo incorrecto desde la app móvil
- **Dead code**: `GET /mobile/v1/health` responde 200 aunque ningún cliente lo usa
- **Sin autenticación**: `curl http://localhost:8000/tickets` devuelve todos los tickets sin credenciales
- **Password hardcodeado**: Con `PDF_PASSWORD` no definida, cualquiera que lea el código conoce la contraseña (`"1234"`)
- **PDF vacío**: `GET /tickets/42/pdf` genera un PDF con "Propietario:" y "Teléfono:" en blanco
- **Passwords en tests**: `tests/conftest.py` contiene `"1234"` hardcodeado — cualquiera que clone el repo conoce la contraseña de producción
- **Rate limiting ausente**: `curl -X POST http://localhost:8000/api/mobile/tickets/1/estado` puede ejecutarse miles de veces por segundo
- **N+1 en resumen**: `GET /api/mobile/tickets/1/resumen` ejecuta 6 queries en lugar de 1-2
- **Schemas inline**: `from app.rutas.mobile_api_ruta import TicketListResponse` viola la separación de responsabilidades

---

## Expected Behavior

### Preservation Requirements

**Unchanged Behaviors:**
- Un ticket finalizado con `total_servicio` definido DEBE seguir calculando `saldo_pendiente = total_servicio - anticipo_recibido - total_cobros` (mínimo 0)
- Un ticket finalizado DEBE seguir creando un `MovimientoCaja` de tipo `INGRESO_FINAL`
- Intentar finalizar un ticket sin `total_servicio` DEBE seguir retornando `400 Bad Request`
- Un cliente autenticado correctamente DEBE seguir recibiendo respuestas normales
- Los endpoints de economía, vehículos, citas y seguridad NO deben verse afectados
- Cuando `PDF_PASSWORD` está definida, DEBE seguir usándose para validar `X-PDF-Password`
- El PDF DEBE seguir mostrando datos del propietario cuando el vehículo los tiene
- Los tests existentes DEBEN seguir pasando cuando `.env.test` está presente
- Peticiones dentro del límite de tasa DEBEN procesarse normalmente
- `GET /api/mobile/tickets/{id}/resumen` DEBE retornar los mismos valores tras la consolidación
- Los schemas DEBEN mantener los mismos campos y validaciones tras ser movidos

---

## Hypothesized Root Cause

1. **Lógica de finalización copiada manualmente**: La lógica de `POST /tickets/{id}/finalizar` fue copiada en `mobile_api_ruta.py` sin extraerla a una función compartida.

2. **Router registrado sin verificar uso**: `mobile_ruta.py` fue creado como prototipo y su registro en `main.py` nunca fue eliminado.

3. **Dependencias de autenticación no aplicadas a nivel de router**: Los routers `/tickets` y `/api/mobile` no incluyen `requerir_password_admin`.

4. **Fallback inseguro en `os.getenv`**: `dependencias.py` usa `os.getenv("PDF_PASSWORD", "1234")` exponiendo la contraseña en el código fuente.

5. **`hasattr()` sobre modelo SQLAlchemy**: `hasattr(ticket, 'nombre_propietario')` retorna `False` porque esos campos residen en `Vehiculo`, no en `Ticket`.

6. **Passwords hardcodeadas en `conftest.py`**: `os.environ.setdefault("PDF_PASSWORD", "1234")` expone las contraseñas de producción en el código fuente. La solución es leer desde `.env.test` (en `.gitignore`) o variables de entorno del sistema.

7. **`slowapi` declarado pero no configurado**: `requirements.txt` incluye `slowapi` pero `app/main.py` no crea el `Limiter` ni registra el handler de `RateLimitExceeded`.

8. **N+1 queries en `obtener_resumen_ticket`**: 4 `COUNT` separados y 2 cargas completas de registros para sumar valores. La solución es consolidar con `func.count()` y `func.sum()`.

9. **Schemas Pydantic inline en el router**: Los 14 schemas de `mobile_api_ruta.py` están definidos en el mismo archivo que los endpoints, violando la separación de responsabilidades.

---

## Correctness Properties

Property 1: Bug Condition — Lógica de finalización unificada

_For any_ ticket con `total_servicio` definido que sea finalizado desde cualquier ruta, la función `_finalizar_ticket` SHALL calcular `saldo_pendiente`, crear el `MovimientoCaja` de tipo `INGRESO_FINAL` y actualizar el estado de forma idéntica.

**Validates: Requirements 2.1, 2.2**

Property 2: Bug Condition — Endpoints de tickets requieren autenticación

_For any_ petición HTTP a `/tickets` o `/api/mobile/tickets` sin cabecera de autenticación correcta, el sistema SHALL retornar `401 Unauthorized`.

**Validates: Requirements 2.4, 2.5**

Property 3: Bug Condition — PDF incluye datos del propietario

_For any_ ticket con `vehiculo_id` válido cuyo vehículo tenga `nombre_propietario` y/o `telefono_propietario`, el PDF SHALL incluir esos valores.

**Validates: Requirements 2.7, 3.4**

Property 4: Preservation — Cálculo de saldo y MovimientoCaja sin regresión

_For any_ ticket finalizado correctamente, `_finalizar_ticket` SHALL CONTINUE TO calcular `saldo_pendiente = total_servicio - anticipo_recibido - total_cobros` (mínimo 0) y crear `MovimientoCaja` de tipo `INGRESO_FINAL`.

**Validates: Requirements 3.1, 3.2, 3.3**

Property 5: Preservation — Clientes autenticados no se ven afectados

_For any_ petición con cabecera de autenticación correcta, el sistema SHALL CONTINUE TO procesar la petición y retornar la respuesta esperada.

**Validates: Requirements 3.5, 3.6**

Property 6: Bug Condition — Tests no exponen contraseñas de producción

_For any_ ejecución de la suite de tests, el sistema SHALL leer `PDF_PASSWORD` y `ADMIN_PASSWORD` desde variables de entorno o `.env.test` (excluido de git), y SHALL NOT tener esos valores hardcodeados en el código fuente.

**Validates: Requirements 1.8, 2.8**

Property 7: Bug Condition — Rate limiting activo en endpoints sensibles

_For any_ cliente que supere el límite de peticiones configurado, el sistema SHALL retornar `429 Too Many Requests`.

**Validates: Requirements 1.9, 2.9**

Property 8: Bug Condition — Query consolidada en resumen de ticket

_For any_ llamada a `GET /api/mobile/tickets/{id}/resumen`, el sistema SHALL ejecutar como máximo 2 queries, retornando los mismos valores que la implementación original con 6 queries.

**Validates: Requirements 1.10, 2.10, 3.10**

Property 9: Bug Condition — Schemas en módulo dedicado

_For any_ importación de schemas del dominio mobile, el sistema SHALL resolverlos desde `app/esquemas/mobile_schema.py`.

**Validates: Requirements 1.11, 2.11, 3.11**

Property 10: Preservation — Resumen retorna valores idénticos tras consolidación

_For any_ ticket con datos en todas las colecciones, la query consolidada SHALL CONTINUE TO retornar exactamente los mismos contadores y sumas financieras.

**Validates: Requirements 3.10**

---

## Fix Implementation

### Changes Required

**Archivos 1–7**: Ya implementados en la iteración anterior (ticket_service.py, ticket_ruta.py, mobile_api_ruta.py, main.py, dependencias.py).

---

**Archivo 8**: `tests/conftest.py`

**Cambios específicos**:
1. Crear `.env.test` en la raíz con `PDF_PASSWORD` y `ADMIN_PASSWORD` reales de test; agregar `.env.test` a `.gitignore`
2. Crear `.env.test.example` con valores placeholder como documentación
3. En `tests/conftest.py`: agregar `from dotenv import load_dotenv` y `load_dotenv(".env.test", override=False)` antes de los `setdefault`
4. Eliminar los valores `"1234"` hardcodeados; usar `os.environ.setdefault("PDF_PASSWORD", "")` como fallback para CI con comentario explicativo

---

**Archivo 9**: `app/main.py` y endpoints sensibles

**Cambios específicos**:
1. Importar: `from slowapi import Limiter, _rate_limit_exceeded_handler`, `from slowapi.util import get_remote_address`, `from slowapi.errors import RateLimitExceeded`
2. Crear: `limiter = Limiter(key_func=get_remote_address)`
3. Registrar: `app.state.limiter = limiter` y `app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)`
4. Aplicar `@limiter.limit("20/minute")` al endpoint `GET /tickets/{id}/pdf` en `ticket_ruta.py`
5. Aplicar `@limiter.limit("30/minute")` a `PATCH /api/mobile/tickets/{id}/estado` en `mobile_api_ruta.py`

---

**Archivo 10**: `app/esquemas/mobile_schema.py` *(nuevo)*

**Cambios específicos**:
1. Crear `app/esquemas/mobile_schema.py` con los 14 schemas: `TicketListResponse`, `TicketDetailResponse`, `ProcesoResponse`, `RepuestoResponse`, `FotoResponse`, `ProcesoCreate`, `RepuestoCreate`, `ActualizarEstadoTicket`, `CompraResponse`, `CompraCreate`, `CobroResponse`, `CobroCreate`, `ActualizarFinanzasData`, `EntregarTicketData`
2. En `app/rutas/mobile_api_ruta.py`: eliminar las 14 definiciones inline y agregar `from app.esquemas.mobile_schema import (...)`

---

**Archivo 11**: `app/rutas/mobile_api_ruta.py` — `obtener_resumen_ticket`

**Cambios específicos**:
1. Importar `func` desde `sqlalchemy`
2. Reemplazar las 6 queries separadas:
   ```python
   from sqlalchemy import func

   total_procesos = db.query(func.count(TicketProceso.id)).filter(
       TicketProceso.ticket_id == ticket_id).scalar()
   total_repuestos = db.query(func.count(TicketRepuesto.id)).filter(
       TicketRepuesto.ticket_id == ticket_id).scalar()
   total_fotos = db.query(func.count(TicketFoto.id)).filter(
       TicketFoto.ticket_id == ticket_id,
       TicketFoto.tipo != "PROCESO").scalar()
   total_compras = db.query(func.count(TicketCompra.id)).filter(
       TicketCompra.ticket_id == ticket_id).scalar()
   total_egresos = db.query(
       func.coalesce(func.sum(TicketCompra.valor), 0)).filter(
       TicketCompra.ticket_id == ticket_id).scalar()
   total_cobros = db.query(
       func.coalesce(func.sum(TicketCobro.valor), 0)).filter(
       TicketCobro.ticket_id == ticket_id).scalar()
   ```
3. Mantener exactamente la misma estructura de respuesta JSON

---

## Testing Strategy

### Property-Based Tests

- Generar combinaciones aleatorias de `(total_servicio, anticipo_recibido, cobros[])` y verificar `saldo_pendiente = max(0, total_servicio - anticipo - sum(cobros))` (Property 4)
- Generar peticiones sin cabecera de auth a `/tickets/*` y verificar que todas retornan 401 (Property 2)
- Generar tickets con vehículos aleatorios y verificar que el PDF incluye datos del propietario (Property 3)
- Generar tickets con cantidades aleatorias de colecciones y verificar que la query consolidada retorna los mismos valores (Property 10)

### Integration Tests

- Rate limiting: enviar más de 20 peticiones/minuto al endpoint de PDF → verificar 429 en la petición 21
- Resumen consolidado: crear ticket con N procesos, M compras y K cobros → verificar contadores y sumas correctos
- Schemas: importar `TicketListResponse` desde `app.esquemas.mobile_schema` sin importar el router
- conftest: verificar que `.env.test` no aparece en `git status`
