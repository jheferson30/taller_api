-- Migración: Agregar datos del vehículo a citas
-- Fecha: 2026-03-13
-- Descripción: Permite guardar datos completos del vehículo al crear una cita

-- Agregar campos del vehículo a la tabla citas
ALTER TABLE citas 
    ADD COLUMN IF NOT EXISTS marca VARCHAR(100),
    ADD COLUMN IF NOT EXISTS modelo VARCHAR(100),
    ADD COLUMN IF NOT EXISTS anio INTEGER,
    ADD COLUMN IF NOT EXISTS cilindraje VARCHAR(50),
    ADD COLUMN IF NOT EXISTS color VARCHAR(50);

-- Hacer placa obligatoria (si hay citas sin placa, se deben corregir primero)
-- ALTER TABLE citas ALTER COLUMN placa SET NOT NULL;

COMMENT ON COLUMN citas.marca IS 'Marca del vehículo (guardada en la cita para referencia)';
COMMENT ON COLUMN citas.modelo IS 'Modelo del vehículo (guardada en la cita para referencia)';
COMMENT ON COLUMN citas.anio IS 'Año del vehículo (guardada en la cita para referencia)';
COMMENT ON COLUMN citas.cilindraje IS 'Cilindraje del vehículo';
COMMENT ON COLUMN citas.color IS 'Color del vehículo';
