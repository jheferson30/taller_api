BEGIN;

-- ==============================
-- TABLA DE COBROS POR TICKET
-- ==============================
CREATE TABLE IF NOT EXISTS ticket_cobros (
    id SERIAL PRIMARY KEY,
    ticket_id INTEGER NOT NULL REFERENCES tickets(id),
    concepto VARCHAR(200) NOT NULL,
    valor INTEGER NOT NULL,
    fecha_creacion TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_ticket_cobros_ticket_id ON ticket_cobros(ticket_id);

COMMIT;
