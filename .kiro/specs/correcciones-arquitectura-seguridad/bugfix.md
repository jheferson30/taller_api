# Bugfix Requirements Document

## Introduction

El backend FastAPI del taller mecánico presenta seis problemas agrupados en tres categorías: arquitectura, seguridad y datos. Los problemas de arquitectura generan deuda técnica y riesgo de divergencia entre rutas; los de seguridad exponen endpoints críticos sin autenticación y credenciales hardcodeadas; el problema de datos hace que el PDF generado nunca muestre el nombre ni el teléfono del cliente.

---

## Bug Analysis

### Current Behavior (Defect)

**Arquitectura — Lógica de finalización duplicada**

1.1 WHEN se finaliza un ticket desde `POST /tickets/{id}/finalizar` THEN el sistema ejecuta la lógica de cálculo de saldo y creación de movimiento de caja definida localmente en `ticket_ruta.py`

1.2 WHEN se finaliza un ticket desde `PATCH /api/mobile/tickets/{id}/estado` con estado `FINALIZADO` THEN el sistema ejecuta una copia independiente de esa misma lógica en `mobile_api_ruta.py`, sin compartir código con la anterior

**Arquitectura — Dead code en router `/mobile/v1`**

1.3 WHEN la aplicación arranca THEN el sistema registra el router `mobile_ruta.py` con prefijo `/mobile/v1` que expone 3 endpoints (`/health`, `/tickets/activos`, `/tickets/{id}/timeline`) que ningún cliente consume

**Seguridad — Endpoints de tickets sin autenticación**

1.4 WHEN cualquier cliente en la red envía una petición a cualquier endpoint bajo `/tickets` THEN el sistema procesa la petición sin verificar ninguna credencial ni token

1.5 WHEN cualquier cliente en la red envía una petición a cualquier endpoint bajo `/api/mobile/tickets` THEN el sistema procesa la petición sin verificar ninguna credencial ni token

**Seguridad — Password PDF hardcodeado**

1.6 WHEN la variable de entorno `PDF_PASSWORD` no está definida THEN el sistema usa el valor literal `"1234"` como contraseña del PDF, expuesto directamente en el código fuente de `dependencias.py`

**Datos — nombre_propietario y telefono_propietario ausentes en el PDF**

1.7 WHEN se genera el PDF de un ticket mediante `GET /tickets/{id}/pdf` THEN el sistema evalúa `hasattr(ticket, 'nombre_propietario')` que siempre retorna `False` porque esos campos no existen en el modelo `Ticket`, por lo que el PDF muestra los campos "Propietario" y "Teléfono" vacíos

---

### Expected Behavior (Correct)

**Arquitectura — Lógica de finalización compartida**

2.1 WHEN se finaliza un ticket desde cualquier ruta THEN el sistema SHALL ejecutar una única función `_finalizar_ticket(ticket, db)` compartida, de modo que un cambio en la lógica se aplique automáticamente a ambas rutas

2.2 WHEN la función `_finalizar_ticket` es invocada THEN el sistema SHALL calcular el saldo pendiente, registrar el movimiento de caja y actualizar el estado del ticket de forma idéntica independientemente del router que la llame

**Arquitectura — Eliminación del router dead code**

2.3 WHEN la aplicación arranca THEN el sistema SHALL NOT registrar el router `mobile_ruta.py` ni exponer los endpoints `/mobile/v1/*`

**Seguridad — Autenticación en endpoints de tickets**

2.4 WHEN un cliente envía una petición a cualquier endpoint bajo `/tickets` sin la cabecera de autenticación correcta THEN el sistema SHALL retornar `401 Unauthorized`

2.5 WHEN un cliente envía una petición a cualquier endpoint bajo `/api/mobile/tickets` sin la cabecera de autenticación correcta THEN el sistema SHALL retornar `401 Unauthorized`

**Seguridad — Password PDF desde variable de entorno obligatoria**

2.6 WHEN la variable de entorno `PDF_PASSWORD` no está definida THEN el sistema SHALL lanzar un error de configuración al arrancar, en lugar de usar un valor por defecto hardcodeado

**Datos — nombre_propietario y telefono_propietario en el PDF**

2.7 WHEN se genera el PDF de un ticket THEN el sistema SHALL obtener `nombre_propietario` y `telefono_propietario` consultando el vehículo asociado al ticket (`vehiculo_id`) y SHALL incluir esos valores en el diccionario `ticket_dict` que se pasa al generador de PDF

---

### Unchanged Behavior (Regression Prevention)

3.1 WHEN un ticket se finaliza con `total_servicio` definido THEN el sistema SHALL CONTINUE TO calcular `saldo_pendiente = total_servicio - anticipo_recibido - total_cobros` con el resultado mínimo de 0

3.2 WHEN un ticket se finaliza THEN el sistema SHALL CONTINUE TO crear un `MovimientoCaja` de tipo `INGRESO_FINAL` con el valor `total_servicio - anticipo_recibido`

3.3 WHEN un ticket no tiene `total_servicio` definido y se intenta finalizar THEN el sistema SHALL CONTINUE TO retornar `400 Bad Request`

3.4 WHEN se genera el PDF de un ticket con `nombre_propietario` y `telefono_propietario` disponibles en el vehículo THEN el sistema SHALL CONTINUE TO incluir esos datos en la sección "INFORMACIÓN DEL VEHÍCULO Y TICKET"

3.5 WHEN un cliente autenticado correctamente accede a cualquier endpoint de tickets THEN el sistema SHALL CONTINUE TO procesar la petición normalmente

3.6 WHEN los endpoints de economía, vehículos, citas y seguridad reciben peticiones THEN el sistema SHALL CONTINUE TO comportarse exactamente igual que antes de los cambios

3.7 WHEN la variable de entorno `PDF_PASSWORD` está definida THEN el sistema SHALL CONTINUE TO usar ese valor para validar la cabecera `X-PDF-Password`
