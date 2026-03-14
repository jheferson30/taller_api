# Plan de Implementación: mobile-compras-ui

## Overview

La imagen del soporte ya se renderiza en `ComprasTab`. Quedan pendientes el placeholder con texto "Sin soporte" cuando `soporte_url` es null, el fallback `onError` para imágenes que fallan al cargar, y los estilos dedicados del diseño.

## Tasks

- [x] 1. Renderizar imagen del soporte en ComprasTab
  - Agregar `Image` importado en `TicketDetailScreen.js`
  - Renderizar `<Image>` con `http://10.0.2.2:8000${c.soporte_url}` cuando `soporte_url` existe
  - _Requirements: 1.1, 3.1, 3.3_

- [ ] 2. Completar manejo de imagen: placeholder y onError
  - [ ] 2.1 Extraer `CompraCard` como función interna con estado `imgError`
    - Reemplazar el bloque inline de cada compra por una función `CompraCard({ compra, editable, onEliminar })`
    - Agregar `useState(false)` para `imgError` dentro de `CompraCard`
    - Mostrar placeholder con texto "Sin soporte" cuando `soporte_url` es null o `imgError` es true
    - Agregar prop `onError={() => setImgError(true)}` al componente `<Image>`
    - _Requirements: 1.2, 3.2_

  - [ ] 2.2 Agregar estilos dedicados al StyleSheet
    - Agregar `compraCard`, `compraSoporteImg`, `compraPlaceholder`, `compraPlaceholderText`, `compraBody`, `compraTitleRow`, `compraTitulo`, `compraPrecio`, `compraResponsable`, `compraNota`, `compraFooter` según el diseño
    - Reemplazar estilos inline de la imagen por `styles.compraSoporteImg`
    - _Requirements: 1.1, 1.3, 1.4_

- [ ] 3. Checkpoint — Verificar que todos los casos visuales funcionan
  - Asegurar que se ven correctamente: compra con imagen, compra sin imagen, error de carga de imagen, botón eliminar en modo editable
  - Asegurar que `fmt(0)` retorna `$0` y no `—`
  - _Requirements: 1.2, 2.2, 3.2_

- [ ]* 4. Escribir property tests para funciones de formato e imagen
  - [ ]* 4.1 Property 1: Formato de precio colombiano
    - **Property 1: Para cualquier entero no negativo, `fmt(v)` comienza con `$` y usa separadores de miles colombianos**
    - **Validates: Requirements 2.1, 2.2, 2.3**

  - [ ]* 4.2 Property 2: Valor cero o nulo muestra $0
    - **Property 2: `fmt(0)` y `fmt(null)` retornan exactamente `$0`**
    - **Validates: Requirements 2.2**

  - [ ]* 4.3 Property 3: URL de imagen construida correctamente
    - **Property 3: Para cualquier `soporte_url` que comience con `/uploads/`, la URI construida es `http://10.0.2.2:8000` + `soporte_url`**
    - **Validates: Requirements 3.1**

  - [ ]* 4.4 Property 4: Compra sin soporte_url muestra placeholder
    - **Property 4: `CompraCard` con `soporte_url` null no renderiza `<Image>` sino el placeholder "Sin soporte"**
    - **Validates: Requirements 1.2, 3.2**

  - [ ]* 4.5 Property 5: Eliminación refresca la lista
    - **Property 5: Al confirmar eliminación, `onRefresh` se invoca exactamente una vez**
    - **Validates: Requirements 4.3**

- [ ] 5. Checkpoint final — Asegurar que todos los tests pasan
  - Ejecutar la suite de tests, preguntar al usuario si hay dudas.

## Notes

- Tareas marcadas con `*` son opcionales (tests)
- La tarea 1 ya está completada — el código en `TicketDetailScreen.js` ya tiene la imagen renderizada
- La tarea 2 es el trabajo pendiente principal
- Para los property tests se requiere instalar `fast-check`: `npm install --save-dev fast-check`
