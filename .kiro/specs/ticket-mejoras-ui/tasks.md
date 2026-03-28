# Implementation Plan: ticket-mejoras-ui

## Overview

Implementación incremental de las cuatro mejoras de UI/UX en el sistema de tickets. Se empieza por el backend (schema + ruta + PDF), luego el frontend web y finalmente la app móvil.

## Tasks

- [x] 1. Backend: Extender schema y endpoint de entrega para aceptar observaciones
  - [x] 1.1 Modificar `TicketEntregarPayload` en `app/esquemas/ticket_schema.py`
    - Añadir campos opcionales: `observaciones_finales`, `recomendaciones`, `proximo_mantenimiento`
    - _Requirements: 3.7_
  - [ ]* 1.2 Escribir unit test para `TicketEntregarPayload`
    - Verificar que el schema acepta los tres campos opcionales con valores nulos y con texto
    - _Requirements: 3.7_
  - [x] 1.3 Modificar el endpoint `marcar_entregado` en `app/rutas/ticket_ruta.py`
    - Antes de cambiar estado a ENTREGADO, guardar `observaciones_finales`, `recomendaciones` y `proximo_mantenimiento` si vienen en el payload
    - _Requirements: 3.8_
  - [ ]* 1.4 Escribir property test para persistencia de observaciones en entrega
    - **Property 5: Persistencia de observaciones en entrega (round-trip)**
    - **Validates: Requirements 3.8**
    - _Requirements: 3.8_

- [ ] 2. Checkpoint — Asegurar que los tests del backend pasan
  - Ejecutar `pytest` en los tests de backend. Preguntar al usuario si hay dudas.

- [x] 3. Backend: Incluir foto_url de procesos en el endpoint de PDF
  - [x] 3.1 Modificar `generar_pdf_cliente` en `app/rutas/ticket_ruta.py`
    - Añadir `'foto_url': p.foto_url` al dict de cada proceso en `procesos_list`
    - _Requirements: 4.6_
  - [ ]* 3.2 Escribir property test para foto_url en procesos_list del PDF
    - **Property 6: foto_url de procesos incluida en datos del PDF**
    - **Validates: Requirements 4.6**
    - _Requirements: 4.6_

- [x] 4. Backend: Mejorar PDF con fotos de procesos en cuadrícula
  - [x] 4.1 Extraer función auxiliar `resolver_ruta_img` en `app/utils/pdf_generator.py`
    - Mover la función inline de resolución de rutas (actualmente dentro de la sección de compras) a nivel de módulo para reutilizarla
    - _Requirements: 4.7_
  - [ ]* 4.2 Escribir property test para resolución de rutas de imágenes
    - **Property 7: Resolución de ruta de imagen de proceso**
    - **Validates: Requirements 4.7**
    - _Requirements: 4.7_
  - [x] 4.3 Reemplazar la sección "PROCESOS REALIZADOS" en `pdf_generator.py` por layout de tarjetas en cuadrícula de 2 columnas
    - Cada tarjeta muestra: foto (si existe y la ruta local existe), nombre, mecánico, descripción
    - Usar el mismo patrón de `POR_FILA = 2` que usa la sección de compras con `POR_FILA = 3`
    - _Requirements: 4.1, 4.2, 4.3_
  - [ ]* 4.4 Escribir property test para layout de 2 columnas en procesos del PDF
    - **Property 8: Layout de procesos en PDF con 2 columnas**
    - **Validates: Requirements 4.3**
    - _Requirements: 4.3_

- [ ] 5. Checkpoint — Verificar que el PDF generado incluye fotos de procesos correctamente
  - Ejecutar `pytest` en los tests de PDF. Preguntar al usuario si hay dudas.

- [ ] 6. Frontend web: Reorganizar tarjeta de proceso con foto arriba
  - [ ] 6.1 Modificar la lista "Procesos Realizados" en `frontend/src/pages/TicketPage.jsx`
    - Mover el bloque `<img>` de `p.foto_url` para que aparezca antes del `<div className="item-header">` (nombre y mecánico)
    - _Requirements: 1.1, 1.2_
  - [ ]* 6.2 Escribir unit test para renderizado de foto en proceso (web)
    - **Property 1: Renderizado de foto en proceso**
    - **Validates: Requirements 1.1, 1.2**
    - _Requirements: 1.1, 1.2_

- [-] 7. Frontend web: Unificar secciones Compras y Repuestos
  - [x] 7.1 Eliminar la pestaña "Compras" del array de tabs en `TicketPage.jsx`
    - Renombrar el tab "Repuestos" para que muestre también el conteo de compras si aplica
    - _Requirements: 2.1_
  - [x] 7.2 Añadir estado `fueComprado` y campos de compra al formulario de repuesto en `TicketPage.jsx`
    - Añadir checkbox/toggle "¿Fue comprado?" con estado local `fueComprado` (default false)
    - Mostrar condicionalmente: campo `valor` (InputDinero), `responsable` (SelectMecanico), `nota` (textarea), `compraFile` (file input)
    - _Requirements: 2.3, 2.5_
  - [x] 7.3 Modificar `onAddRepuesto` en `TicketPage.jsx` para crear compra si `fueComprado`
    - Si `fueComprado === true` y `valor > 0`: después de `api.agregarRepuesto(...)`, llamar a `api.agregarCompra(...)` con `descripcion = repuesto.nombre`
    - _Requirements: 2.7, 2.9_
  - [ ]* 7.4 Escribir property tests para lógica de guardado de repuesto con/sin compra (web)
    - **Property 2: Guardar repuesto sin compra cuando Toggle_Comprado está desactivado**
    - **Property 3: Guardar repuesto con compra cuando Toggle_Comprado está activado**
    - **Validates: Requirements 2.7, 2.8, 2.9, 2.10**
    - _Requirements: 2.7, 2.9_
  - [x] 7.5 Añadir badge "🛒 Comprado" en la lista de repuestos de `TicketPage.jsx`
    - Calcular `nombresComprados = new Set(resumen.compras.map(c => c.descripcion))` y mostrar badge si `nombresComprados.has(r.nombre)`
    - _Requirements: 2.11_
  - [x] 7.6 Eliminar el bloque TAB: COMPRAS del JSX de `TicketPage.jsx`
    - Eliminar el bloque `{activeTab === "compras" && ...}` completo
    - _Requirements: 2.1_

- [ ] 8. Frontend web: Mover Observaciones Finales a sección Entrega
  - [x] 8.1 Eliminar el bloque "Observaciones Finales" del tab `finanzas` en `TicketPage.jsx`
    - Eliminar el `<div className="form-section">` con los tres campos de observaciones que está al final del tab finanzas
    - _Requirements: 3.1, 3.3_
  - [x] 8.2 Añadir los tres campos de observaciones al tab `entrega` en `TicketPage.jsx`
    - Añadir antes del botón "Marcar como Entregado": campos `observaciones_finales`, `recomendaciones`, `proximo_mantenimiento` usando el estado `observaciones` existente
    - _Requirements: 3.1, 3.4_
  - [x] 8.3 Modificar `onEntregar` en `TicketPage.jsx` para incluir observaciones en el payload
    - Pasar `...observaciones` junto con `entrega` al llamar `api.entregarTicket(selectedId, { ...entrega, ...observaciones })`
    - _Requirements: 3.5_
  - [ ]* 8.4 Escribir property test para payload de entrega con observaciones (web)
    - **Property 4: Campos de observaciones en payload de entrega**
    - **Validates: Requirements 3.5**
    - _Requirements: 3.5_

- [ ] 9. Checkpoint — Verificar que el frontend web funciona correctamente
  - Ejecutar `npm run build` en `frontend/`. Preguntar al usuario si hay dudas.

- [ ] 10. App móvil: Reorganizar tarjeta de proceso con foto arriba
  - [ ] 10.1 Verificar y ajustar el orden en `ProcesosTab` de `TicketDetailScreen.js`
    - Confirmar que `<Image>` de `p.foto_url` aparece antes de `<Text style={styles.itemTitle}>`. Si no, reordenar.
    - _Requirements: 1.3, 1.4_
  - [ ]* 10.2 Escribir unit test para renderizado de foto en proceso (móvil)
    - **Property 1: Renderizado de foto en proceso**
    - **Validates: Requirements 1.3, 1.4**
    - _Requirements: 1.3, 1.4_

- [x] 11. App móvil: Unificar Compras y Repuestos en AddRepuestoScreen
  - [ ] 11.1 Añadir estado `fueComprado` y campos de compra a `AddRepuestoScreen.js`
    - Importar `Switch` de React Native
    - Añadir estado: `fueComprado` (bool, false), `valor` (string), `responsable` (string), `nota` (string), `uri` (null)
    - Mostrar `Switch` con label "¿Fue comprado?" después del campo marca/referencia
    - Mostrar condicionalmente los campos de compra cuando `fueComprado === true`
    - _Requirements: 2.4, 2.6_
  - [ ] 11.2 Añadir lógica de foto de soporte en `AddRepuestoScreen.js`
    - Importar `expo-image-picker`
    - Añadir botones "📷 Cámara" y "🖼 Galería" (igual que `AddCompraScreen.js`)
    - Mostrar preview de la imagen seleccionada
    - _Requirements: 2.6_
  - [ ] 11.3 Modificar `handleGuardar` en `AddRepuestoScreen.js` para crear compra si `fueComprado`
    - Si `fueComprado === true` y `valor > 0`: después de `api.createRepuesto(...)`, llamar a `api.createCompra(ticketId, { descripcion: nombre, valor, responsable, nota }, uri)`
    - _Requirements: 2.8, 2.10_
  - [ ]* 11.4 Escribir property tests para lógica de guardado de repuesto con/sin compra (móvil)
    - **Property 2: Guardar repuesto sin compra cuando Toggle_Comprado está desactivado**
    - **Property 3: Guardar repuesto con compra cuando Toggle_Comprado está activado**
    - **Validates: Requirements 2.8, 2.10**
    - _Requirements: 2.8, 2.10_

- [ ] 12. App móvil: Unificar tabs Compras y Repuestos en TicketDetailScreen
  - [ ] 12.1 Fusionar `RepuestosTab` y `ComprasTab` en `TicketDetailScreen.js`
    - Renombrar el tab "Compras" eliminándolo del array `TABS`
    - En `RepuestosTab`, añadir badge "🛒 Comprado" si el nombre del repuesto coincide con alguna compra
    - Pasar `compras` como prop a `RepuestosTab` para el matching por nombre
    - _Requirements: 2.2, 2.12_
  - [ ] 12.2 Eliminar `ComprasTab` y su referencia en el render de `TicketDetailScreen.js`
    - Eliminar la función `ComprasTab` y el bloque `{tab === 'compras' && ...}`
    - _Requirements: 2.2_

- [ ] 13. App móvil: Verificar campos de observaciones en EntregaTab
  - [ ] 13.1 Verificar que `EntregaTab` en `TicketDetailScreen.js` envía los campos de observaciones
    - Confirmar que `api.entregarTicket(ticketId, { confirmado_entrega_por, observaciones_finales, recomendaciones, proximo_mantenimiento })` incluye los tres campos
    - Con el cambio del schema en la tarea 1.1, el backend ya los acepta
    - _Requirements: 3.6_

- [ ] 14. Checkpoint final — Verificar que todo funciona end-to-end
  - Ejecutar todos los tests (`pytest` backend, `npm run test -- --run` frontend). Preguntar al usuario si hay dudas.

## Notes

- Las tareas marcadas con `*` son opcionales y pueden omitirse para un MVP más rápido
- No se requieren migraciones de base de datos
- La asociación repuesto-compra se hace por coincidencia de nombre (sin FK adicional)
- El badge "🛒 Comprado" es una mejora visual; si el nombre del repuesto difiere de la descripción de la compra, no se mostrará (comportamiento aceptable)
- Property tests usan `pytest + hypothesis` (backend) y `vitest + @testing-library/react` (frontend)
