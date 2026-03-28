# Design Document: ticket-mejoras-ui

## Overview

Este documento describe el diseño técnico para las cuatro mejoras de UI/UX en la página de tickets del sistema de taller mecánico. El sistema usa FastAPI (backend), React (web) y React Native/Expo (móvil).

Las mejoras son:
1. Procesos con foto en tarjeta visual
2. Unificación de Compras y Repuestos en una sola sección
3. Mover Observaciones Finales a la sección Entrega
4. PDF mejorado con fotos de procesos y observaciones

## Architecture

El sistema sigue una arquitectura de tres capas:

```
[React Web / React Native Mobile]
         ↓ HTTP REST
[FastAPI Backend (ticket_ruta.py)]
         ↓ SQLAlchemy ORM
[PostgreSQL / SQLite]
         ↓ (PDF)
[pdf_generator.py → ReportLab]
```

Los cambios afectan las tres capas:
- **Frontend web**: `TicketPage.jsx` — UI de tabs, formularios, listas
- **Frontend móvil**: `TicketDetailScreen.js`, `AddRepuestoScreen.js` — pantallas de detalle y formularios
- **Backend**: `ticket_schema.py` (schema Pydantic), `ticket_ruta.py` (endpoint entregar), `pdf_generator.py` (generación PDF)

No se requieren migraciones de base de datos: todos los campos necesarios ya existen (`foto_url` en `ticket_procesos`, campos de observaciones en `tickets`).

## Components and Interfaces

### Mejora 1: Procesos con foto

**Web (`TicketPage.jsx`):**
- La lista de procesos ya renderiza `p.foto_url` con una `<img>` debajo del header. Se reorganiza para que la imagen quede **encima** del nombre, como una tarjeta tipo card.
- Estructura de tarjeta:
  ```
  ┌─────────────────────────┐
  │  [FOTO si existe]       │
  ├─────────────────────────┤
  │  Nombre del proceso     │
  │  Mecánico               │
  │  Descripción            │
  └─────────────────────────┘
  ```

**Móvil (`TicketDetailScreen.js` → `ProcesosTab`):**
- Ya renderiza `p.foto_url` con `<Image>` antes del nombre. El orden ya es correcto. Se verifica y ajusta el estilo si es necesario.

### Mejora 2: Unificación Compras/Repuestos

**Estrategia de asociación repuesto-compra:**
Dado que el modelo de BD no tiene una FK directa entre `ticket_repuestos` y `ticket_compras`, la asociación se hace por **nombre/descripción**: cuando se crea un repuesto con `fue_comprado=true`, se crea una compra con `descripcion` igual al nombre del repuesto. Para mostrar el badge "Comprado" en la lista, se hace un match por nombre entre repuestos y compras del mismo ticket.

**Web (`TicketPage.jsx`):**
- Eliminar pestaña "Compras", renombrar "Repuestos" a "Repuestos".
- En el formulario de agregar repuesto, añadir:
  - Toggle/checkbox `fueComprado` (estado local)
  - Campos condicionales: `valor`, `responsable`, `nota`, `compraFile` (visibles solo si `fueComprado === true`)
- En `onAddRepuesto`: si `fueComprado`, después de crear el repuesto, llamar también a `api.agregarCompra(...)`.
- En la lista de repuestos: mostrar badge "🛒 Comprado" si el nombre del repuesto coincide con alguna compra del ticket.

**Móvil (`AddRepuestoScreen.js`):**
- Añadir estado `fueComprado` (boolean, default false).
- Añadir Switch de React Native con label "¿Fue comprado?".
- Campos condicionales: `valor`, `responsable`, `nota`, `uri` (foto soporte).
- En `handleGuardar`: si `fueComprado`, llamar también a `api.createCompra(...)`.

**Móvil (`TicketDetailScreen.js`):**
- Renombrar tab "Compras" a "Repuestos" y fusionar `RepuestosTab` y `ComprasTab`.
- La nueva `RepuestosTab` muestra la lista de repuestos con badge si fue comprado, y el botón navega a `AddRepuesto`.
- Eliminar tab "Compras" y `ComprasTab`.

### Mejora 3: Observaciones a Entrega

**Web (`TicketPage.jsx`):**
- Eliminar el bloque "Observaciones Finales" de la sección `finanzas` (actualmente está al final del tab Finanzas).
- Añadir los tres campos (`observaciones_finales`, `recomendaciones`, `proximo_mantenimiento`) en el tab `entrega`, antes del botón "Marcar como Entregado".
- El estado `observaciones` se mueve a ser parte del payload de entrega.
- En `onEntregar`: incluir los campos de observaciones en el payload enviado a `api.entregarTicket(...)`.

**Backend (`ticket_schema.py`):**
- Extender `TicketEntregarPayload` con los tres campos opcionales:
  ```python
  observaciones_finales: Optional[str] = Field(None, max_length=800)
  recomendaciones: Optional[str] = Field(None, max_length=800)
  proximo_mantenimiento: Optional[str] = Field(None, max_length=200)
  ```

**Backend (`ticket_ruta.py` → `marcar_entregado`):**
- Antes de cambiar el estado a ENTREGADO, guardar los campos de observaciones si vienen en el payload:
  ```python
  if datos.observaciones_finales is not None:
      ticket.observaciones_finales = datos.observaciones_finales
  # idem para recomendaciones y proximo_mantenimiento
  ```

**Móvil (`TicketDetailScreen.js` → `EntregaTab`):**
- Ya tiene los tres campos implementados y los envía en `api.entregarTicket(...)`. Solo requiere que el backend los acepte (cambio de schema).

### Mejora 4: PDF mejorado

**Backend (`ticket_ruta.py` → `generar_pdf_cliente`):**
- Añadir `foto_url` a cada dict en `procesos_list`:
  ```python
  procesos_list = [{'nombre': p.nombre, 'mecanico': p.mecanico, 'descripcion': p.descripcion, 'foto_url': p.foto_url} for p in procesos]
  ```

**Backend (`pdf_generator.py`):**
- Reemplazar la sección "PROCESOS REALIZADOS" (actualmente una tabla simple) por un layout de tarjetas en cuadrícula (2 columnas), similar al layout de compras.
- Cada tarjeta muestra: foto (si existe, resuelta a ruta local), nombre, mecánico, descripción.
- Reutilizar la función `resolver_ruta_img` (actualmente inline en la sección de compras) extrayéndola como función auxiliar del módulo.

## Data Models

No se requieren cambios en los modelos de base de datos. Todos los campos necesarios ya existen:

| Tabla | Campo | Estado |
|-------|-------|--------|
| `ticket_procesos` | `foto_url` | ✅ Existe |
| `tickets` | `observaciones_finales` | ✅ Existe |
| `tickets` | `recomendaciones` | ✅ Existe |
| `tickets` | `proximo_mantenimiento` | ✅ Existe |
| `ticket_repuestos` | todos los campos | ✅ Existe |
| `ticket_compras` | todos los campos | ✅ Existe |

La asociación repuesto-compra se hace en memoria por coincidencia de nombre, sin FK adicional.

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system — essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Renderizado de foto en proceso

*For any* lista de procesos donde al menos un proceso tiene `foto_url` no nulo, el componente de lista debe incluir un elemento `<img>` (web) o `<Image>` (móvil) con la URL de la foto para ese proceso, y no debe incluir imagen para los procesos sin `foto_url`.

**Validates: Requirements 1.1, 1.2, 1.3, 1.4**

### Property 2: Guardar repuesto sin compra cuando Toggle_Comprado está desactivado

*For any* repuesto con nombre y cantidad válidos y `fue_comprado = false`, el flujo de guardado debe llamar exactamente una vez al endpoint de repuestos y cero veces al endpoint de compras.

**Validates: Requirements 2.7, 2.8**

### Property 3: Guardar repuesto con compra cuando Toggle_Comprado está activado

*For any* repuesto con nombre y cantidad válidos y `fue_comprado = true` con valor de compra mayor a cero, el flujo de guardado debe llamar exactamente una vez al endpoint de repuestos y exactamente una vez al endpoint de compras, con la descripción de la compra igual al nombre del repuesto.

**Validates: Requirements 2.9, 2.10**

### Property 4: Campos de observaciones en payload de entrega

*For any* combinación de valores para `observaciones_finales`, `recomendaciones` y `proximo_mantenimiento` (incluyendo nulos), el payload enviado al endpoint de entrega debe contener exactamente esos valores.

**Validates: Requirements 3.5, 3.6**

### Property 5: Persistencia de observaciones en entrega (round-trip)

*For any* ticket en estado FINALIZADO, al llamar al endpoint `/tickets/{id}/entregar` con valores de observaciones, el ticket resultante debe tener esos mismos valores en sus campos `observaciones_finales`, `recomendaciones` y `proximo_mantenimiento`.

**Validates: Requirements 3.8**

### Property 6: foto_url de procesos incluida en datos del PDF

*For any* lista de procesos con `foto_url` (nulo o no nulo), la lista `procesos_list` construida en el endpoint de PDF debe contener el campo `foto_url` para cada proceso, con el mismo valor que tiene en la base de datos.

**Validates: Requirements 4.6**

### Property 7: Resolución de ruta de imagen de proceso

*For any* URL de foto de proceso con formato `/uploads/...` o `http://127.0.0.1:8000/uploads/...`, la función de resolución de rutas debe devolver una ruta relativa del sistema de archivos con prefijo `uploads/`.

**Validates: Requirements 4.7**

### Property 8: Layout de procesos en PDF con 2 columnas

*For any* lista de N procesos (N ≥ 1), el número de filas generadas en la sección de procesos del PDF debe ser igual a `ceil(N / 2)`.

**Validates: Requirements 4.3**

## Error Handling

- Si `foto_url` de un proceso es nulo o la ruta local no existe, el PDF omite la imagen y muestra solo los datos textuales (comportamiento ya implementado para compras).
- Si el toggle "¿Fue comprado?" está activo pero el valor es 0 o vacío, el formulario debe mostrar un error de validación y no enviar la petición.
- Si la creación del repuesto tiene éxito pero la creación de la compra falla, se muestra un mensaje de error al usuario. El repuesto queda guardado (no se hace rollback del repuesto).
- Si el payload de entrega incluye observaciones con longitud mayor al límite del schema, el backend retorna 422 con detalle del campo inválido.

## Testing Strategy

### Dual Testing Approach

Se usan dos tipos de tests complementarios:

**Unit tests** — para ejemplos específicos, casos borde y estructura de UI:
- Verificar que el tab "Compras" no existe y el tab "Repuestos" sí existe (Req 2.1, 2.2)
- Verificar que el formulario de repuesto contiene el toggle "¿Fue comprado?" (Req 2.3, 2.4)
- Verificar que al activar el toggle aparecen los campos de compra (Req 2.5, 2.6)
- Verificar que la sección Finalizar no contiene los campos de observaciones (Req 3.1, 3.3)
- Verificar que `TicketEntregarPayload` acepta los campos de observaciones (Req 3.7)
- Verificar que el PDF incluye la sección de observaciones cuando el ticket las tiene (Req 4.4, 4.5)

**Property tests** — para propiedades universales (Properties 1–8 del diseño):
- Librería: **pytest + hypothesis** (Python, para backend y lógica de PDF)
- Para frontend: **vitest + @testing-library/react** con mocks de API
- Mínimo 100 iteraciones por property test (configurado con `@settings(max_examples=100)` en Hypothesis)

**Property Test Tags:**
Cada property test debe incluir un comentario con el formato:
`# Feature: ticket-mejoras-ui, Property N: <texto de la propiedad>`

**Configuración Hypothesis:**
```python
from hypothesis import given, settings, strategies as st

@settings(max_examples=100)
@given(st.lists(st.fixed_dictionaries({
    'nombre': st.text(min_size=1),
    'mecanico': st.one_of(st.none(), st.text()),
    'descripcion': st.one_of(st.none(), st.text()),
    'foto_url': st.one_of(st.none(), st.text(min_size=1)),
})))
def test_property_1_foto_en_proceso(procesos):
    # Feature: ticket-mejoras-ui, Property 1: Renderizado de foto en proceso
    ...
```
