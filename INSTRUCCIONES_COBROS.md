# Instrucciones para Implementar Sistema de Cobros

## 1. Ejecutar Migración de Base de Datos

Ejecuta el siguiente comando para crear la tabla de cobros:

```bash
psql -U tu_usuario -d tu_base_datos -f db/migracion_cobros_2026_03_11.sql
```

O si usas otro método, ejecuta manualmente:

```sql
CREATE TABLE IF NOT EXISTS ticket_cobros (
    id SERIAL PRIMARY KEY,
    ticket_id INTEGER NOT NULL REFERENCES tickets(id),
    concepto VARCHAR(200) NOT NULL,
    valor INTEGER NOT NULL,
    fecha_creacion TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_ticket_cobros_ticket_id ON ticket_cobros(ticket_id);
```

## 2. Reiniciar el Backend

```bash
# Detén el servidor si está corriendo
# Ctrl+C

# Inicia nuevamente
uvicorn app.main:app --reload
```

## 3. Reiniciar el Frontend

```bash
cd frontend

# Detén el servidor si está corriendo
# Ctrl+C

# Inicia nuevamente
npm run dev
```

## 4. Probar la Funcionalidad

1. Ve a la página de Tickets
2. Selecciona un ticket abierto o en proceso
3. Ve a la pestaña "Finanzas"
4. Verás una nueva sección "Items de Cobro"
5. Agrega items como:
   - Concepto: "Mantenimiento"
   - Valor: 150000
6. Agrega más items si quieres
7. El total se calculará automáticamente
8. Al finalizar el ticket y generar el PDF, verás el detalle de cobros

## 5. Características Implementadas

✅ Nueva tabla `ticket_cobros` en la base de datos
✅ Endpoints en el backend:
   - POST /tickets/{ticket_id}/cobros - Agregar cobro
   - DELETE /tickets/{ticket_id}/cobros/{cobro_id} - Eliminar cobro
✅ Interfaz en el frontend para agregar/eliminar cobros
✅ Cálculo automático del total basado en los cobros
✅ Los cobros aparecen en el PDF del cliente
✅ Solo se pueden agregar/eliminar cobros en tickets editables (ABIERTO/EN_PROCESO)

## 6. Flujo de Trabajo

1. **Agregar procesos, repuestos, fotos** - Trabajo técnico
2. **Registrar compras** - Egresos del taller
3. **Definir cobros** - Items que se le cobrarán al cliente:
   - Mantenimiento: $150,000
   - Mano de obra: $50,000
   - Diagnóstico: $30,000
   - Total automático: $230,000
4. **Actualizar finanzas** - Confirmar total y método de pago
5. **Finalizar ticket** - Genera el cobro en caja
6. **PDF del cliente** - Muestra el detalle de cobros

## 7. Ejemplo de PDF

```
Comprobante de servicio - Taller
Ticket: TK-ABC123-20260311120000
Placa: ABC123
...

Detalle de cobros:
- Mantenimiento: $150,000
- Mano de obra: $50,000
- Diagnóstico: $30,000

Total servicio: $230,000
Anticipo: $50,000
Saldo final: $180,000
```

## Notas Importantes

- Los cobros NO crean movimientos de caja (solo son items del ticket)
- Los egresos (compras) SÍ crean movimientos de caja
- El total del servicio puede ser diferente a la suma de cobros (puedes ajustarlo manualmente)
- La ganancia estimada = Total servicio - Total egresos
