-- Migración: agregar columna cobros_rapidos a configuracion_taller
ALTER TABLE configuracion_taller ADD COLUMN IF NOT EXISTS cobros_rapidos TEXT DEFAULT '[]';
