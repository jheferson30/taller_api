# Documento de Requerimientos

## Introducción

Mejora de la pantalla de compras en la app móvil (React Native / Expo) para que la visualización de compras registradas sea similar a la versión web. Actualmente, la pestaña "Compras" en `TicketDetailScreen` muestra las compras como tarjetas de texto plano. La versión web muestra una tarjeta visual con imagen del soporte (factura/recibo), nombre del ítem en negrita, precio en rojo y responsable. Esta mejora busca paridad visual entre ambas plataformas.

## Glosario

- **ComprasTab**: Componente dentro de `TicketDetailScreen.js` que lista las compras de un ticket.
- **AddCompraScreen**: Pantalla de la app móvil para registrar una nueva compra con descripción, valor, responsable, nota e imagen de soporte.
- **Compra**: Registro de un gasto asociado a un ticket, que incluye descripción, valor, responsable opcional, nota opcional y soporte fotográfico opcional.
- **Soporte**: Imagen (factura, recibo u otro comprobante) adjunta a una compra.
- **CompraCard**: Tarjeta visual que representa una compra en la lista, con imagen, nombre, precio y responsable.
- **API_Mobile**: Backend FastAPI que expone los endpoints `/api/mobile/tickets/{id}/compras`.
- **Precio_Rojo**: Convención visual donde el valor monetario de una compra se muestra en color rojo (`#dc2626`) para destacarlo.

---

## Requerimientos

### Requerimiento 1: Tarjeta visual de compra con imagen

**User Story:** Como mecánico, quiero ver las compras registradas con su imagen de soporte visible, para identificar rápidamente cada compra sin tener que abrir un detalle separado.

#### Criterios de Aceptación

1. WHEN una compra tiene `soporte_url` definido, THE ComprasTab SHALL mostrar la imagen del soporte en la parte superior de la CompraCard con dimensiones mínimas de 160px de alto y ancho completo de la tarjeta.
2. WHEN una compra no tiene `soporte_url`, THE ComprasTab SHALL mostrar un área de placeholder con el texto "Sin soporte" en lugar de la imagen.
3. THE CompraCard SHALL mostrar el campo `descripcion` de la compra en texto negrita como título principal de la tarjeta.
4. THE CompraCard SHALL mostrar el campo `valor` formateado como moneda colombiana (ej: `$30.000`) en color rojo (`#dc2626`) alineado a la derecha del título.
5. WHEN el campo `responsable` de una compra no es nulo, THE CompraCard SHALL mostrar el texto "Responsable: [nombre]" debajo del título en color secundario (`#64748b`).
6. WHEN el campo `nota` de una compra no es nulo, THE CompraCard SHALL mostrar la nota debajo del responsable en texto secundario.

---

### Requerimiento 2: Formato de precio consistente

**User Story:** Como mecánico, quiero ver los precios de las compras en formato de moneda colombiana, para leer los valores de forma clara y consistente con la versión web.

#### Criterios de Aceptación

1. THE ComprasTab SHALL formatear todos los valores numéricos de compras usando `toLocaleString('es-CO')` con el prefijo `$`.
2. WHEN el valor de una compra es `0` o nulo, THE ComprasTab SHALL mostrar `$0` en lugar de un campo vacío.
3. THE CompraCard SHALL mostrar el precio en el mismo color rojo (`colors.error` = `#dc2626`) que usa la versión web.

---

### Requerimiento 3: Carga de imagen del soporte desde el servidor

**User Story:** Como mecánico, quiero que la imagen del soporte se cargue automáticamente desde el servidor, para no tener que navegar a otra pantalla para verla.

#### Criterios de Aceptación

1. WHEN `soporte_url` de una compra comienza con `/uploads/`, THE ComprasTab SHALL construir la URL completa concatenando la base del servidor (ej: `http://10.0.2.2:8000`) con el valor de `soporte_url`.
2. WHEN la imagen del soporte no puede cargarse, THE ComprasTab SHALL mostrar el área de placeholder con el texto "Sin soporte" sin interrumpir la visualización de las demás compras.
3. THE CompraCard SHALL cargar la imagen con `resizeMode="cover"` para mantener proporciones correctas dentro de la tarjeta.

---

### Requerimiento 4: Acción de eliminar compra integrada en la tarjeta

**User Story:** Como mecánico, quiero poder eliminar una compra directamente desde su tarjeta visual, para gestionar las compras sin perder el contexto visual.

#### Criterios de Aceptación

1. WHILE el ticket está en estado `ABIERTO` o `EN_PROCESO`, THE CompraCard SHALL mostrar un botón de eliminar accesible dentro de la tarjeta.
2. WHEN el usuario presiona el botón de eliminar, THE ComprasTab SHALL mostrar un diálogo de confirmación antes de ejecutar la eliminación.
3. WHEN la eliminación es confirmada, THE ComprasTab SHALL llamar a `api.eliminarCompra` y refrescar la lista de compras.
4. IF la eliminación falla, THEN THE ComprasTab SHALL mostrar un mensaje de error mediante `Alert.alert`.

---

### Requerimiento 5: Confirmación visual tras registrar una compra

**User Story:** Como mecánico, quiero ver una confirmación visual después de guardar una compra, para saber que el registro fue exitoso antes de volver a la lista.

#### Criterios de Aceptación

1. WHEN la compra se guarda exitosamente en `AddCompraScreen`, THE AddCompraScreen SHALL navegar de regreso a la pantalla anterior (`navigation.goBack()`).
2. WHEN `AddCompraScreen` navega de regreso, THE ComprasTab SHALL recargar automáticamente la lista de compras gracias al `useFocusEffect` existente en `TicketDetailScreen`.
3. THE AddCompraScreen SHALL mostrar un `ActivityIndicator` mientras la petición al servidor está en curso para dar retroalimentación al usuario.
4. IF el servidor retorna un error al guardar la compra, THEN THE AddCompraScreen SHALL mostrar el mensaje de error con `Alert.alert` sin navegar de regreso.
