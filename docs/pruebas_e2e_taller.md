# Pruebas E2E Rapidas (Recepcion + Proceso + Economia)

## 1) Variables

```bash
export BASE_URL="http://127.0.0.1:8000"
export PDF_PASSWORD="1234"
export ADMIN_PASSWORD="1234"
```

En PowerShell:

```powershell
$env:BASE_URL="http://127.0.0.1:8000"
$env:PDF_PASSWORD="1234"
$env:ADMIN_PASSWORD="1234"
```

## 2) Migrar DB

Ejecuta el SQL:

- Archivo: `db/migracion_2026_02_28.sql`

## 3) Levantar API

```bash
uvicorn app.main:app --reload
```

## 4) Flujo Pagina 2 (Recepcion)

### Buscar por placa
```bash
curl "$BASE_URL/vehiculos/buscar?placa=ABC123"
```

### Crear vehiculo
```bash
curl -X POST "$BASE_URL/vehiculos/" \
  -H "Content-Type: application/json" \
  -d '{
    "placa":"ABC123",
    "marca":"Yamaha",
    "modelo":"FZ",
    "anio":2022,
    "cilindraje":"150cc",
    "color":"Negro",
    "nombre_propietario":"Carlos",
    "telefono_propietario":"3001234567"
  }'
```

### Actualizar vehiculo
```bash
curl -X PUT "$BASE_URL/vehiculos/ABC123" \
  -H "Content-Type: application/json" \
  -d '{"telefono_propietario":"3000000000","color":"Azul"}'
```

### Crear ticket de ingreso con anticipo
```bash
curl -X POST "$BASE_URL/vehiculos/ABC123/ticket-ingreso" \
  -H "Content-Type: application/json" \
  -d '{
    "motivo_visita":"Falla en freno delantero",
    "observaciones_recepcion":"ruido metalico",
    "kilometraje":12000,
    "estado_inicial":"freno blando",
    "anticipo_recibido":50000,
    "metodo_pago_anticipo":"EFECTIVO",
    "recepcionado_por":"Laura"
  }'
```

### Ficha con historial
```bash
curl "$BASE_URL/vehiculos/ABC123/ficha"
```

## 5) Flujo Pagina 3 (Proceso)

### Listar abiertos
```bash
curl "$BASE_URL/tickets/abiertos"
```

### Buscar ticket
```bash
curl "$BASE_URL/tickets/buscar?placa=ABC123"
```

Toma el `id` del ticket y reemplaza `:ticket_id`.

### Agregar proceso
```bash
curl -X POST "$BASE_URL/tickets/:ticket_id/procesos" \
  -H "Content-Type: application/json" \
  -d '{"nombre":"Cambio de aceite","descripcion":"aceite 20w50","mecanico":"Juan"}'
```

### Agregar repuesto
```bash
curl -X POST "$BASE_URL/tickets/:ticket_id/repuestos" \
  -H "Content-Type: application/json" \
  -d '{"nombre":"Filtro de aceite","cantidad":1,"marca_referencia":"Yamalube"}'
```

### Agregar foto evidencia
```bash
curl -X POST "$BASE_URL/tickets/:ticket_id/fotos" \
  -H "Content-Type: application/json" \
  -d '{"tipo":"ANTES","archivo_url":"https://mi-bucket/fotos/antes1.jpg","descripcion":"freno delantero"}'
```

### Registrar compra (crea egreso en caja)
```bash
curl -X POST "$BASE_URL/tickets/:ticket_id/compras" \
  -H "Content-Type: application/json" \
  -d '{
    "descripcion":"Pastillas de freno",
    "valor":35000,
    "soporte_url":"https://mi-bucket/soportes/factura1.jpg",
    "nota":"compra local",
    "responsable":"Juan"
  }'
```

### Definir finanzas
```bash
curl -X PUT "$BASE_URL/tickets/:ticket_id/finanzas" \
  -H "Content-Type: application/json" \
  -d '{"total_servicio":180000,"metodo_pago_final":"NEQUI"}'
```

### Observaciones finales
```bash
curl -X PUT "$BASE_URL/tickets/:ticket_id/observaciones-finales" \
  -H "Content-Type: application/json" \
  -d '{
    "observaciones_finales":"se recomienda revisar nuevamente en 15 dias",
    "recomendaciones":"evitar frenado brusco por 48h",
    "proximo_mantenimiento":"2026-04"
  }'
```

### Finalizar ticket (crea ingreso final)
```bash
curl -X POST "$BASE_URL/tickets/:ticket_id/finalizar"
```

### PDF cliente
```bash
curl "$BASE_URL/tickets/:ticket_id/pdf" --output ticket_cliente.pdf
```

### Entregar ticket
```bash
curl -X POST "$BASE_URL/tickets/:ticket_id/entregar" \
  -H "Content-Type: application/json" \
  -d '{"confirmado_entrega_por":"Carlos","firma_entrega_url":"https://mi-bucket/firmas/firma1.png"}'
```

## 6) Validar Economia (Pagina 1)

### Resumen diario
```bash
curl "$BASE_URL/economia-dia"
```

### Ingresos detalle
```bash
curl "$BASE_URL/economia-dia/ingresos"
```

### Egresos detalle
```bash
curl "$BASE_URL/economia-dia/egresos"
```

### PDF de cierre diario (con password)
```bash
curl "$BASE_URL/economia-dia/pdf" \
  -H "X-PDF-Password: $PDF_PASSWORD" \
  --output cierre_diario.pdf
```

### Historico (admin)
```bash
curl "$BASE_URL/economia-dia/historico?fecha_desde=2026-02-01&fecha_hasta=2026-02-28" \
  -H "X-Admin-Password: $ADMIN_PASSWORD"
```

## 7) API movil base

```bash
curl "$BASE_URL/mobile/v1/health"
curl "$BASE_URL/mobile/v1/tickets/activos"
curl "$BASE_URL/mobile/v1/tickets/:ticket_id/timeline"
```
