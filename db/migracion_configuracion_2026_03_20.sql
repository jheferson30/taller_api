-- Migración: Mecánicos y Configuración del Taller
-- Fecha: 2026-03-20

CREATE TABLE IF NOT EXISTS mecanicos (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    activo BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS configuracion_taller (
    id INTEGER PRIMARY KEY DEFAULT 1,
    nombre_taller VARCHAR(200) NOT NULL DEFAULT 'Taller Mecánico',
    direccion VARCHAR(300),
    telefono VARCHAR(50),
    nit VARCHAR(50),
    procesos_rapidos TEXT DEFAULT '[]'
);

-- Insertar fila única de configuración si no existe
INSERT INTO configuracion_taller (id, nombre_taller, direccion, telefono, nit, procesos_rapidos)
VALUES (1, 'Taller Mecánico', '', '', '', '[]')
ON CONFLICT (id) DO NOTHING;
