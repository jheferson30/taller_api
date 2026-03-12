# Migración: Vehículos desde Citas

## Problema Resuelto
Los vehículos agregados desde la página de citas no quedaban guardados en la base de datos porque el modelo `Vehiculo` requería campos obligatorios (`marca`, `modelo`, `anio`) que no están disponibles en el formulario de citas.

## Cambios Realizados

### 1. Modelo de Vehículo (`app/modelos/vehiculo.py`)
- Campos `marca`, `modelo` y `anio` ahora son opcionales (nullable=True)
- Permite crear vehículos con solo placa y datos del propietario

### 2. Esquema de Vehículo (`app/esquemas/vehiculo_schema.py`)
- Campos `marca`, `modelo` y `anio` ahora son Optional
- Mantiene compatibilidad con el resto del sistema

### 3. Migración SQL (`db/migracion_vehiculos_opcionales_2026_03_12.sql`)
- Actualiza la base de datos para permitir valores NULL en marca, modelo y anio

## Pasos para Aplicar la Migración

### Opción 1: Usando psql (PostgreSQL)
```bash
psql -U tu_usuario -d tu_base_datos -f db/migracion_vehiculos_opcionales_2026_03_12.sql
```

### Opción 2: Desde pgAdmin o DBeaver
1. Abre tu herramienta de gestión de base de datos
2. Conecta a tu base de datos
3. Ejecuta el contenido del archivo `db/migracion_vehiculos_opcionales_2026_03_12.sql`

### Opción 3: Desde Python
```python
import psycopg2

conn = psycopg2.connect(
    host="localhost",
    database="tu_base_datos",
    user="tu_usuario",
    password="tu_password"
)

with open('db/migracion_vehiculos_opcionales_2026_03_12.sql', 'r') as f:
    sql = f.read()
    
with conn.cursor() as cur:
    cur.execute(sql)
    conn.commit()

conn.close()
```

## Verificación

Después de aplicar la migración, reinicia el servidor backend:

```bash
# Detener el servidor si está corriendo
# Ctrl+C

# Iniciar nuevamente
uvicorn app.main:app --reload
```

## Flujo Actualizado

1. Usuario crea una cita con placa, nombre y teléfono del cliente
2. Al generar ticket desde la cita:
   - Si el vehículo existe: se usa el existente
   - Si no existe: se crea uno nuevo con los datos disponibles (placa, nombre, teléfono)
3. El vehículo queda guardado en la base de datos
4. Los datos faltantes (marca, modelo, año) se pueden completar después desde la página principal

## Notas Importantes

- Los vehículos creados desde citas tendrán marca, modelo y año en NULL
- Esto no afecta el funcionamiento del sistema
- Se recomienda completar estos datos posteriormente para tener un registro completo
- El sistema sigue funcionando normalmente con vehículos que tienen todos los datos
