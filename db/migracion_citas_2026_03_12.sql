-- Migración: Sistema de citas
-- Fecha: 2026-03-12
-- Descripción: Tabla para gestionar citas programadas y convertirlas en tickets

CREATE TABLE IF NOT EXISTS citas (
    id SERIAL PRIMARY KEY,
    vehiculo_id INTEGER REFERENCES vehiculos(id),
    placa VARCHAR(20),
    nombre_cliente VARCHAR(150) NOT NULL,
    telefono_cliente VARCHAR(50) NOT NULL,
    fecha_cita TIMESTAMP WITH TIME ZONE NOT NULL,
    motivo VARCHAR(250) NOT NULL,
    observaciones VARCHAR(500),
    estado VARCHAR(20) DEFAULT 'PENDIENTE' NOT NULL,
    ticket_id INTEGER REFERENCES tickets(id),
    ticket_codigo VARCHAR(40),
    creado_por VARCHAR(120),
    fecha_creacion TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    fecha_actualizacion TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_citas_placa ON citas(placa);
CREATE INDEX idx_citas_fecha ON citas(fecha_cita);
CREATE INDEX idx_citas_estado ON citas(estado);
CREATE INDEX idx_citas_ticket ON citas(ticket_id);

COMMENT ON TABLE citas IS 'Citas programadas para mantenimiento de vehículos';
COMMENT ON COLUMN citas.estado IS 'Estados: PENDIENTE, CONFIRMADA, CANCELADA, CONVERTIDA';
COMMENT ON COLUMN citas.ticket_id IS 'ID del ticket si la cita fue convertida';
