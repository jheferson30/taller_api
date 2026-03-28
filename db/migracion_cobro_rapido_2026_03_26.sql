-- Migración: agregar tipo INGRESO_RAPIDO al enum tipo_movimiento
-- PostgreSQL no permite ALTER TYPE dentro de una transacción con tablas que lo usan,
-- por eso se hace así:
ALTER TYPE tipomovimiento ADD VALUE IF NOT EXISTS 'INGRESO_RAPIDO';
