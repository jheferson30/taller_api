# PDF Completo con Fotos Implementado

## ✅ Sistema de PDF Profesional Mejorado

Hemos mejorado el PDF del cliente con diseño limpio y profesional:

1. **Diseño en gris** - Colores profesionales y limpios
2. **Todos los datos** - Muestra todos los campos incluso si están vacíos
3. **Procesos con observaciones** - Tablas grises con descripciones completas sin desbordamiento
4. **Repuestos completos** - Incluye repuestos normales + compras con cantidad, marca y valor
5. **Compras con imágenes** - 3 por fila, imágenes de 30mm
6. **Fotos de evidencia** - 2 por fila, tamaño proporcional, etiquetas ANTES/DESPUES
7. **Detalle de cobros** - Tabla limpia y profesional
8. **Resumen financiero** - Información clara de pagos

## Instalación

### 1. Instalar nuevas dependencias

```bash
pip install reportlab pillow
```

O reinstalar desde requirements.txt:

```bash
pip install -r requirements.txt
```

### 2. Reiniciar el backend

```bash
uvicorn app.main:app --reload
```

### 3. Reiniciar el frontend

```bash
cd frontend
npm run dev
```

## Cómo Usar

### Desde la Interfaz Web

1. Ve a **Tickets** → Selecciona un ticket **FINALIZADO**
2. Ve a la pestaña **Entrega**
3. Verás un botón grande: **📄 Descargar PDF Completo**
4. Click en el botón → Se descarga el PDF

### Desde la API

```bash
curl http://127.0.0.1:8000/tickets/{ticket_id}/pdf --output ticket.pdf
```

## Contenido del PDF

### Información Completa del Servicio

1. **Encabezado**
   - Título: "COMPROBANTE DE SERVICIO"
   - Subtítulo: "Taller Mecánico"

2. **Información del Vehículo y Ticket**
   - Código del ticket, Placa
   - Estado, Fecha de ingreso
   - Kilometraje, Estado inicial
   - Propietario, Teléfono
   - Motivo de visita
   - Observaciones de recepción
   - Todos los campos se muestran incluso si están vacíos

3. **Procesos Realizados**
   - Tabla con: Proceso, Mecánico, Observaciones
   - Fondo gris en encabezado
   - Filas alternadas en gris claro
   - Las observaciones usan Paragraph para que no se desborden

4. **Repuestos Utilizados**
   - Combina repuestos normales + repuestos de compras
   - Tabla con: Repuesto, Cantidad, Marca/Ref, Valor
   - Los repuestos normales muestran "-" en valor
   - Los de compras muestran el valor pagado
   - Fondo gris en encabezado

5. **Compras Realizadas**
   - 3 compras por fila
   - Imágenes de 30mm (proporcionales)
   - Descripción y valor debajo de cada imagen
   - Responsable en letra pequeña
   - Cuadros con bordes grises

6. **Evidencia Fotográfica**
   - 2 fotos por fila
   - Etiquetas: ANTES / DESPUES / OTRA
   - Descripción de cada foto
   - Imágenes proporcionales (máx 3" de ancho)
   - Tamaño visible pero no excesivo

7. **Detalle de Cobros**
   - Tabla limpia con: Concepto, Valor
   - Fondo gris en encabezado
   - Filas alternadas
   - Total destacado en gris oscuro

8. **Resumen Financiero**
   - Total del servicio
   - Anticipo recibido
   - Saldo pendiente
   - Método de pago

9. **Observaciones Finales**
   - Observaciones finales del mecánico o taller
   - Notas importantes sobre el servicio realizado
   - Solo se muestra si hay contenido

10. **Recomendaciones y Próxima Cita**
   - Recomendaciones para el cliente
   - Próximo mantenimiento / Cita programada
   - Fondo gris claro para destacar
   - Solo se muestra si hay contenido

## Características Técnicas

- **Librería**: ReportLab (PDF profesional)
- **Tamaño**: Carta (Letter)
- **Márgenes**: 0.5 pulgadas
- **Fuentes**: Helvetica, Helvetica-Bold
- **Colores**: Paleta gris profesional
  - Gris oscuro (#7f8c8d) - Total de cobros
  - Gris medio (#95a5a6) - Encabezados de tablas
  - Gris claro (#d5dbdb) - Títulos de sección
  - Gris muy claro (#ecf0f1) - Filas alternadas
  - Gris borde (#bdc3c7) - Bordes de tablas
- **Imágenes**: 
  - Compras: 30mm proporcional
  - Fotos: 3" de ancho máximo, proporcional
- **Formato**: PDF 1.4
- **Texto**: Usa Paragraph para evitar desbordamiento en observaciones

## Manejo de Imágenes

El sistema intenta cargar las imágenes de tres formas:

1. **URL completa**: `http://127.0.0.1:8000/uploads/fotos/imagen.jpg`
2. **Ruta relativa**: `/uploads/fotos/imagen.jpg`
3. **Ruta local**: `uploads/fotos/imagen.jpg`

Si la imagen no se puede cargar:
- Muestra el tipo y descripción
- Indica "Imagen no disponible"
- No rompe el PDF

## Ejemplo Visual del PDF

```
┌─────────────────────────────────────────────────────┐
│         COMPROBANTE DE SERVICIO                     │
│         Taller Mecánico                             │
├─────────────────────────────────────────────────────┤
│ INFORMACIÓN DEL VEHÍCULO Y TICKET                   │
│ ┌──────────────┬──────────┬──────────┬──────────┐  │
│ │ Ticket:      │ TK-123   │ Placa:   │ ABC123   │  │
│ │ Estado:      │ FINALIZ. │ Fecha:   │ 11/03/26 │  │
│ │ Kilometraje: │ 50000    │ Estado:  │ Bueno    │  │
│ │ Propietario: │ Cliente  │ Teléfono:│ 3001234  │  │
│ │ Motivo:      │ Mantenimiento preventivo         │  │
│ └──────────────┴──────────┴──────────┴──────────┘  │
├─────────────────────────────────────────────────────┤
│ PROCESOS REALIZADOS                                 │
│ ┌─────────┬──────────┬──────────────────────────┐  │
│ │ Proceso │ Mecánico │ Observaciones            │  │
│ ├─────────┼──────────┼──────────────────────────┤  │
│ │Cambio..│ Juan     │ Se cambió aceite 20W50   │  │
│ │Frenos  │ Pedro    │ Pastillas en buen estado │  │
│ └─────────┴──────────┴──────────────────────────┘  │
├─────────────────────────────────────────────────────┤
│ REPUESTOS UTILIZADOS                                │
│ ┌──────────────┬──────┬──────────┬──────────────┐  │
│ │ Repuesto     │ Cant │ Marca    │ Valor        │  │
│ ├──────────────┼──────┼──────────┼──────────────┤  │
│ │Aceite 20W50  │  1   │ Mobil    │ -            │  │
│ │Filtro aceite │  1   │ Mann     │ $35,000      │  │
│ └──────────────┴──────┴──────────┴──────────────┘  │
├─────────────────────────────────────────────────────┤
│ COMPRAS REALIZADAS                                  │
│ ┌──────────┬──────────┬──────────┐                 │
│ │ [IMG]    │ [IMG]    │ [IMG]    │ (30mm c/u)     │
│ │ Filtro   │ Aceite   │ Bujías   │                 │
│ │ $35,000  │ $45,000  │ $28,000  │                 │
│ └──────────┴──────────┴──────────┘                 │
├─────────────────────────────────────────────────────┤
│ EVIDENCIA FOTOGRÁFICA                               │
│ ┌────────────────────┬────────────────────┐        │
│ │ ANTES              │ DESPUES            │        │
│ │ Freno delantero    │ Freno delantero    │        │
│ │ [IMAGEN 3"]        │ [IMAGEN 3"]        │        │
│ └────────────────────┴────────────────────┘        │
├─────────────────────────────────────────────────────┤
│ DETALLE DE COBROS                                   │
│ ┌──────────────────────────┬──────────────────┐    │
│ │ Concepto                 │ Valor            │    │
│ ├──────────────────────────┼──────────────────┤    │
│ │ Mantenimiento preventivo │ $150,000         │    │
│ │ Mano de obra             │ $50,000          │    │
│ ├──────────────────────────┼──────────────────┤    │
│ │ TOTAL                    │ $200,000         │    │
│ └──────────────────────────┴──────────────────┘    │
├─────────────────────────────────────────────────────┤
│ RESUMEN FINANCIERO                                  │
│ ┌──────────────────────┬──────────────┐            │
│ │ Total del Servicio:  │ $200,000     │            │
│ │ Anticipo Recibido:   │ $100,000     │            │
│ │ Saldo Pendiente:     │ $100,000     │            │
│ │ Método de Pago:      │ Efectivo     │            │
│ └──────────────────────┴──────────────┘            │
├─────────────────────────────────────────────────────┤
│ OBSERVACIONES FINALES                               │
│ ┌─────────────────────────────────────────────┐    │
│ │ El vehículo quedó en excelentes condiciones │    │
│ │ Se recomienda revisar nuevamente en 5000km  │    │
│ └─────────────────────────────────────────────┘    │
├─────────────────────────────────────────────────────┤
│ RECOMENDACIONES Y PRÓXIMA CITA                      │
│ ┌─────────────────────────────────────────────┐    │
│ │ Recomendaciones:                            │    │
│ │ Revisar nivel de líquido de frenos          │    │
│ │ Cambiar filtro de aire en próximo servicio │    │
│ │                                             │    │
│ │ Próximo Mantenimiento / Cita:               │    │
│ │ 15 de Abril de 2026 - Cambio de aceite     │    │
│ └─────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────┘
```

## Ventajas del Nuevo PDF

✅ Diseño profesional en gris (limpio y elegante)
✅ Muestra todos los campos incluso si están vacíos
✅ Observaciones completas sin desbordamiento de texto
✅ Repuestos combinados (normales + compras) con valores
✅ Compras con imágenes pequeñas (30mm), 3 por fila
✅ Fotos con etiquetas ANTES/DESPUES, 2 por fila
✅ Observaciones finales del servicio
✅ Recomendaciones claras para el cliente
✅ Próxima cita / mantenimiento programado visible
✅ Fácil de leer y entender
✅ Listo para imprimir o enviar por email
✅ Genera confianza en el cliente

## Notas Importantes

- Las fotos deben estar en la carpeta `uploads/fotos/`
- Si una foto no se encuentra, el PDF se genera igual
- El PDF se genera al momento de la descarga
- No se guarda en el servidor (se genera dinámicamente)
- Tamaño típico: 200KB - 2MB (dependiendo de las fotos)

## Solución de Problemas

### Error: "Module 'reportlab' not found"
```bash
pip install reportlab pillow
```

### Las imágenes no aparecen en el PDF
- Verifica que las fotos estén en `uploads/fotos/`
- Verifica que las URLs en la base de datos sean correctas
- Revisa los logs del backend para ver errores

### El PDF se descarga vacío
- Verifica que el ticket tenga datos
- Revisa los logs del backend
- Prueba con un ticket que tenga procesos y fotos
