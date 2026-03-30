-- Migración: Integración WhatsApp Business
-- Requerimiento 1.1: Extender ConfiguracionTaller con campos de WhatsApp Business

ALTER TABLE configuracion_taller
  ADD COLUMN whatsapp_token     TEXT,
  ADD COLUMN whatsapp_phone_id  VARCHAR(50),
  ADD COLUMN whatsapp_enabled   BOOLEAN NOT NULL DEFAULT FALSE;

-- Migración: Tabla de log de notificaciones WhatsApp
-- Requerimiento 7.1: Registrar cada intento de envío con resultado y detalle

CREATE TABLE log_notificacion (
    id               SERIAL PRIMARY KEY,
    ticket_id        INTEGER REFERENCES tickets(id) ON DELETE SET NULL,
    telefono_destino VARCHAR(30),
    tipo_evento      VARCHAR(20) NOT NULL,  -- RECEPCION, FINALIZACION, ENTREGA, MANUAL, ENTRANTE
    mensaje_enviado  TEXT,
    resultado        VARCHAR(10) NOT NULL,  -- ENVIADO, ERROR, OMITIDO
    error_detalle    TEXT,
    created_at       TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_log_notificacion_ticket_id ON log_notificacion(ticket_id);
CREATE INDEX idx_log_notificacion_created_at ON log_notificacion(created_at DESC);
