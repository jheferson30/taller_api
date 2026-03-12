-- Migración: Hacer campos opcionales en vehículos
-- Fecha: 2026-03-12
-- Descripción: Permite crear vehículos desde citas sin todos los datos completos

-- Hacer campos opcionales en la tabla vehiculos
ALTER TABLE vehiculos 
    ALTER COLUMN marca DROP NOT NULL,
    ALTER COLUMN modelo DROP NOT NULL,
    ALTER COLUMN anio DROP NOT NULL;

COMMENT ON COLUMN vehiculos.marca IS 'Marca del vehículo (opcional, se puede completar después)';
COMMENT ON COLUMN vehiculos.modelo IS 'Modelo del vehículo (opcional, se puede completar después)';
COMMENT ON COLUMN vehiculos.anio IS 'Año del vehículo (opcional, se puede completar después)';
