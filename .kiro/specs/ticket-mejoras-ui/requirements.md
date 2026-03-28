# Requirements Document

## Introduction

Esta feature agrupa cuatro mejoras de UI/UX en la página de tickets del sistema de taller mecánico (web React + app móvil React Native + backend FastAPI). Los cambios son: (1) mostrar la foto del proceso como tarjeta visual en la lista de procesos realizados, (2) unificar las secciones "Compras" y "Repuestos" en una sola sección "Repuestos" con un toggle "¿Fue comprado?", (3) mover los campos de observaciones finales, recomendaciones y próximo mantenimiento a la sección "Entrega", y (4) mejorar el PDF del ticket para incluir fotos de procesos y los campos de observaciones/recomendaciones/próximo mantenimiento.

## Glossary

- **TicketPage**: Página web React que gestiona el detalle de un ticket activo.
- **TicketDetailScreen**: Pantalla móvil React Native que gestiona el detalle de un ticket.
- **AddRepuestoScreen**: Pantalla móvil para agregar un repuesto a un ticket.
- **Proceso**: Trabajo técnico realizado en el vehículo, puede tener una foto asociada (`foto_url`).
- **Repuesto**: Pieza o material utilizado en el servicio.
- **Compra**: Egreso registrado cuando un repuesto fue adquirido, con valor, responsable, nota y soporte fotográfico.
- **Repuesto_Comprado**: Repuesto que además fue comprado; combina los datos de Repuesto y Compra en un solo flujo.
- **PDF_Generator**: Módulo Python (`pdf_generator.py`) que genera el comprobante PDF del ticket.
- **Sección_Entrega**: Pestaña/sección del ticket donde se registra la entrega del vehículo al cliente.
- **Sección_Finalizar**: Pestaña/sección del ticket donde se finaliza el ticket y se muestra el resumen financiero.
- **Toggle_Comprado**: Control UI (switch/checkbox) que indica si un repuesto fue comprado externamente.

## Requirements

### Requirement 1: Procesos con foto en tarjeta visual

**User Story:** Como mecánico o recepcionista, quiero ver la foto del proceso encima del nombre en la lista de procesos realizados, para identificar visualmente cada trabajo de forma rápida.

#### Acceptance Criteria

1. WHEN la lista de procesos realizados se renderiza en TicketPage, THE TicketPage SHALL mostrar cada proceso como una tarjeta con la foto (si existe) en la parte superior, seguida del nombre, mecánico y descripción.
2. WHEN un proceso no tiene foto asociada (`foto_url` es nulo), THE TicketPage SHALL mostrar la tarjeta del proceso sin imagen, solo con nombre, mecánico y descripción.
3. WHEN la lista de procesos realizados se renderiza en TicketDetailScreen, THE TicketDetailScreen SHALL mostrar cada proceso como una tarjeta con la foto (si existe) en la parte superior, seguida del nombre, mecánico y descripción.
4. WHEN un proceso no tiene foto en TicketDetailScreen, THE TicketDetailScreen SHALL mostrar la tarjeta sin imagen.
5. THE TicketPage SHALL mostrar la foto del proceso con ancho completo de la tarjeta y altura máxima de 220px con `object-fit: cover`.
6. THE TicketDetailScreen SHALL mostrar la foto del proceso con ancho completo de la tarjeta y altura de 180px con `resizeMode: cover`.

### Requirement 2: Unificación de Compras y Repuestos

**User Story:** Como técnico, quiero agregar repuestos y registrar si fueron comprados en un solo flujo, para no tener que navegar entre dos secciones separadas.

#### Acceptance Criteria

1. THE TicketPage SHALL reemplazar las pestañas separadas "Repuestos" y "Compras" por una única pestaña llamada "Repuestos".
2. THE TicketDetailScreen SHALL reemplazar las pestañas separadas "Repuestos" y "Compras" por una única pestaña llamada "Repuestos".
3. WHEN un usuario agrega un repuesto en TicketPage, THE TicketPage SHALL mostrar un toggle o checkbox con la pregunta "¿Fue comprado?".
4. WHEN un usuario agrega un repuesto en AddRepuestoScreen, THE AddRepuestoScreen SHALL mostrar un toggle o switch con la pregunta "¿Fue comprado?".
5. WHEN el Toggle_Comprado está activado en TicketPage, THE TicketPage SHALL mostrar los campos adicionales: valor, responsable, nota y soporte (foto/archivo).
6. WHEN el Toggle_Comprado está activado en AddRepuestoScreen, THE AddRepuestoScreen SHALL mostrar los campos adicionales: valor, responsable, nota y foto de soporte.
7. WHEN el Toggle_Comprado está desactivado, THE TicketPage SHALL guardar únicamente el repuesto sin crear una compra asociada.
8. WHEN el Toggle_Comprado está desactivado, THE AddRepuestoScreen SHALL guardar únicamente el repuesto sin crear una compra asociada.
9. WHEN el Toggle_Comprado está activado y el usuario guarda, THE TicketPage SHALL crear el repuesto y adicionalmente crear una compra con los datos de valor, responsable, nota y soporte.
10. WHEN el Toggle_Comprado está activado y el usuario guarda, THE AddRepuestoScreen SHALL crear el repuesto y adicionalmente crear una compra con los datos de valor, responsable, nota y soporte.
11. THE TicketPage SHALL mostrar en la lista unificada de repuestos un indicador visual (badge o etiqueta) en los repuestos que tienen una compra asociada.
12. THE TicketDetailScreen SHALL mostrar en la lista unificada de repuestos un indicador visual en los repuestos que tienen una compra asociada.

### Requirement 3: Mover Observaciones a Sección Entrega

**User Story:** Como recepcionista, quiero ingresar las observaciones finales, recomendaciones y próximo mantenimiento en la sección de entrega, para que esos datos queden registrados en el momento de entregar el vehículo.

#### Acceptance Criteria

1. THE TicketPage SHALL mover los campos "Observaciones Finales", "Recomendaciones" y "Próximo Mantenimiento" de la sección Finalizar a la sección Entrega.
2. THE TicketDetailScreen SHALL mostrar los campos "Observaciones Finales", "Recomendaciones" y "Próximo Mantenimiento" en la pestaña Entrega (ya están ahí; se debe verificar que no aparezcan en otra sección).
3. THE TicketPage SHALL mostrar en la sección Finalizar únicamente el resumen financiero y el botón de finalizar ticket.
4. WHEN el ticket está en estado FINALIZADO o ENTREGADO, THE TicketPage SHALL mostrar los campos de observaciones en la sección Entrega en modo solo lectura si ya tienen valor.
5. WHEN el usuario guarda la entrega en TicketPage, THE TicketPage SHALL enviar los campos observaciones_finales, recomendaciones y proximo_mantenimiento junto con el payload de entrega al endpoint `/tickets/{id}/entregar`.
6. WHEN el usuario guarda la entrega en TicketDetailScreen, THE TicketDetailScreen SHALL enviar los campos observaciones_finales, recomendaciones y proximo_mantenimiento junto con el payload de entrega (ya implementado; verificar que el endpoint los acepte).
7. THE TicketEntregarPayload (backend schema) SHALL aceptar los campos opcionales observaciones_finales, recomendaciones y proximo_mantenimiento.
8. WHEN se recibe el payload de entrega con observaciones, THE ticket_ruta SHALL guardar esos campos en el ticket antes de cambiar el estado a ENTREGADO.

### Requirement 4: PDF mejorado con fotos de procesos y observaciones

**User Story:** Como cliente, quiero recibir un PDF que muestre cada proceso con su foto, descripción y mecánico, además de las observaciones finales y recomendaciones, para tener un comprobante completo del servicio.

#### Acceptance Criteria

1. WHEN el PDF_Generator renderiza la sección de procesos, THE PDF_Generator SHALL mostrar cada proceso en un cuadro individual con su foto (si existe), nombre, mecánico y descripción.
2. WHEN un proceso no tiene foto, THE PDF_Generator SHALL mostrar el cuadro del proceso sin imagen, solo con nombre, mecánico y descripción.
3. THE PDF_Generator SHALL agrupar los procesos en filas de hasta 2 columnas para aprovechar el ancho de página.
4. WHEN el ticket tiene observaciones_finales, THE PDF_Generator SHALL incluir la sección "OBSERVACIONES FINALES" en el PDF (ya existe; verificar que los datos lleguen correctamente desde el endpoint).
5. WHEN el ticket tiene recomendaciones o proximo_mantenimiento, THE PDF_Generator SHALL incluir la sección "RECOMENDACIONES" en el PDF (ya existe; verificar que los datos lleguen correctamente).
6. THE ticket_ruta SHALL incluir los campos foto_url de cada proceso en la lista `procesos_list` enviada al PDF_Generator.
7. THE PDF_Generator SHALL resolver la ruta local del archivo de foto del proceso de la misma forma que resuelve las fotos de compras (convirtiendo URL a ruta de sistema de archivos).
