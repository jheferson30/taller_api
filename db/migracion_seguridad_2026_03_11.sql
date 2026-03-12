-- Migración: Sistema de seguridad para economía
-- Fecha: 2026-03-11
-- Descripción: Tabla para almacenar contraseñas y palabras clave de recuperación

CREATE TABLE IF NOT EXISTS configuracion_seguridad (
    id SERIAL PRIMARY KEY,
    clave VARCHAR(50) UNIQUE NOT NULL,
    valor_hash VARCHAR(255) NOT NULL,
    fecha_creacion TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    fecha_actualizacion TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_configuracion_seguridad_clave ON configuracion_seguridad(clave);

COMMENT ON TABLE configuracion_seguridad IS 'Almacena configuraciones de seguridad como contraseñas hasheadas';
COMMENT ON COLUMN configuracion_seguridad.clave IS 'Identificador único de la configuración (ej: economia_password)';
COMMENT ON COLUMN configuracion_seguridad.valor_hash IS 'Valor hasheado con SHA256';
