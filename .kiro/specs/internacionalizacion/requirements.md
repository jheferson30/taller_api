# Documento de Requisitos: Internacionalización (i18n)

## Introducción

Este documento describe los requisitos para la internacionalización del sistema SaaS de gestión de talleres mecánicos.

Cada taller tiene su propia configuración regional: **moneda** (ISO 4217), **idioma** (ISO 639-1) y **zona horaria** (IANA). Esta configuración afecta todo el sistema: PDFs generados, mensajes de WhatsApp, emails, reportes económicos y presentación de fechas. Los mensajes de error de la API no se traducen — el frontend maneja sus propias traducciones.

---

## Glosario

- **Moneda**: Código ISO 4217 de 3 caracteres en mayúsculas (ej. `COP`, `USD`, `MXN`, `PEN`).
- **Idioma**: Código ISO 639-1 de 2 caracteres en minúsculas (ej. `es`, `en`, `pt`).
- **Timezone**: Zona horaria IANA (ej. `America/Bogota`, `America/Mexico_City`, `America/Lima`).
- **Locale**: Combinación de idioma y región que determina el formato de números, fechas y moneda.
- **Contexto_Regional**: Objeto que contiene `moneda`, `idioma` y `timezone` del taller del usuario autenticado, disponible en cada request.
- **Documento_Localizado**: PDF, mensaje de WhatsApp o email generado usando el Contexto_Regional del taller.

---

## Requisitos

### Requisito 1: Configuración Regional por Taller

**User Story:** Como ADMIN del taller, quiero configurar la moneda, idioma y zona horaria de mi taller, para que todos los documentos y reportes usen mi configuración regional.

#### Criterios de Aceptación

1. THE Sistema SHALL extender la tabla `configuracion_taller` con los campos: `moneda` (string 3, código ISO 4217, NOT NULL, default `COP`), `idioma` (string 2, código ISO 639-1, NOT NULL, default `es`), `timezone` (string, zona horaria IANA, NOT NULL, default `America/Bogota`).
2. WHEN el ADMIN del taller actualiza `moneda`, THE Sistema SHALL validar que sea un código ISO 4217 válido de exactamente 3 caracteres en mayúsculas.
3. WHEN el ADMIN del taller actualiza `idioma`, THE Sistema SHALL validar que sea un código ISO 639-1 válido de exactamente 2 caracteres en minúsculas.
4. WHEN el ADMIN del taller actualiza `timezone`, THE Sistema SHALL validar que sea una zona horaria IANA válida usando la librería `zoneinfo` de Python.
5. IF se proporciona un valor inválido para `moneda`, `idioma` o `timezone`, THEN THE Sistema SHALL retornar HTTP 422 con un mensaje descriptivo que indique el campo inválido y el formato esperado.
6. THE Sistema SHALL registrar cambios de configuración regional en Audit_Log con acción `CONFIG_CHANGE` incluyendo valores anteriores y nuevos en `details`.
7. THE Sistema SHALL exponer los idiomas soportados mediante `GET /configuracion/idiomas-disponibles` que retorne la lista de códigos ISO 639-1 soportados por el sistema.
8. THE Sistema SHALL exponer las monedas soportadas mediante `GET /configuracion/monedas-disponibles` que retorne la lista de códigos ISO 4217 soportados.

---

### Requisito 2: Contexto Regional en Requests

**User Story:** Como desarrollador, quiero que el contexto regional del taller esté disponible en cada request autenticado, para que los servicios puedan generar documentos localizados sin consultar la BD en cada operación.

#### Criterios de Aceptación

1. THE AuthMiddleware SHALL cargar la `configuracion_taller` del usuario autenticado e inyectar `request.state.moneda`, `request.state.idioma` y `request.state.timezone` en cada request.
2. WHEN el AuthMiddleware carga la configuración regional, THE Sistema SHALL usar una sola query que obtenga `moneda`, `idioma` y `timezone` junto con la verificación del usuario.
3. IF la `configuracion_taller` del taller no existe, THEN THE AuthMiddleware SHALL usar los valores por defecto: `moneda = COP`, `idioma = es`, `timezone = America/Bogota`.
4. THE Sistema SHALL hacer disponible el Contexto_Regional a todos los servicios que generan documentos (PDF, WhatsApp, email) sin requerir parámetros adicionales en sus firmas.

---

### Requisito 3: PDFs Localizados

**User Story:** Como propietario del taller, quiero que los PDFs de tickets usen la moneda, idioma y zona horaria de mi taller, para que los documentos sean correctos para mis clientes.

#### Criterios de Aceptación

1. WHEN el sistema genera un PDF de ticket, THE Sistema SHALL usar el `timezone` del taller para formatear todas las fechas (fecha_ingreso, fecha_cierre, fecha_entrega).
2. WHEN el sistema genera un PDF de ticket, THE Sistema SHALL usar la `moneda` del taller para mostrar los valores monetarios (total_servicio, anticipo_recibido, saldo_pendiente) con el símbolo y formato correcto.
3. WHEN el sistema genera un PDF de ticket, THE Sistema SHALL usar el `idioma` del taller para las etiquetas de texto del documento (ej. "Fecha de ingreso" en español, "Entry date" en inglés).
4. THE Sistema SHALL soportar al menos los idiomas `es` (español) y `en` (inglés) para los PDFs en la versión inicial.
5. THE Sistema SHALL formatear los valores monetarios según el locale del taller: punto como separador de miles y coma como decimal para `es`, coma como separador de miles y punto como decimal para `en`.

---

### Requisito 4: Mensajes de WhatsApp Localizados

**User Story:** Como propietario del taller, quiero que los mensajes de WhatsApp enviados a mis clientes estén en el idioma de mi taller, para que la comunicación sea natural para mis clientes.

#### Criterios de Aceptación

1. WHEN el sistema envía un mensaje de WhatsApp de recepción de vehículo, THE Sistema SHALL usar el `idioma` del taller para seleccionar la plantilla de mensaje correcta.
2. WHEN el sistema envía un mensaje de WhatsApp de finalización de servicio, THE Sistema SHALL incluir el valor del saldo pendiente formateado con la `moneda` del taller.
3. WHEN el sistema envía un mensaje de WhatsApp de entrega de vehículo, THE Sistema SHALL usar el `idioma` del taller para el mensaje de confirmación.
4. THE Sistema SHALL soportar al menos los idiomas `es` (español) y `en` (inglés) para los mensajes de WhatsApp en la versión inicial.
5. THE Sistema SHALL mantener las plantillas de mensajes de WhatsApp en un archivo de configuración separado por idioma, no hardcodeadas en el código.

---

### Requisito 5: Reportes Económicos Localizados

**User Story:** Como ADMIN del taller, quiero que los reportes económicos usen la zona horaria y moneda de mi taller, para que los datos sean correctos para mi contexto.

#### Criterios de Aceptación

1. WHEN el sistema genera el reporte de histórico económico, THE Sistema SHALL agrupar los movimientos por fecha usando el `timezone` del taller, no UTC.
2. WHEN el sistema retorna valores monetarios en endpoints de economía, THE Sistema SHALL incluir el código de `moneda` del taller en la respuesta para que el frontend pueda formatear correctamente.
3. WHEN el sistema calcula "tickets del mes actual" para métricas, THE Sistema SHALL usar el mes calendario en el `timezone` del taller, no en UTC.
4. THE Sistema SHALL incluir `timezone` y `moneda` en la respuesta de `GET /configuracion/taller` para que el frontend pueda usar la configuración regional correcta.

---

### Requisito 6: Emails Localizados

**User Story:** Como usuario del taller, quiero recibir emails del sistema en el idioma de mi taller, para que la comunicación sea natural.

#### Criterios de Aceptación

1. WHEN el sistema envía un email de recuperación de contraseña, THE Sistema SHALL usar el `idioma` del taller del usuario para seleccionar la plantilla de email correcta.
2. THE Sistema SHALL soportar al menos los idiomas `es` (español) y `en` (inglés) para los emails en la versión inicial.
3. THE Sistema SHALL mantener las plantillas de email en archivos separados por idioma, no hardcodeadas en el código.
4. IF el `idioma` del taller no tiene plantilla de email disponible, THEN THE Sistema SHALL usar el idioma `es` como fallback.
