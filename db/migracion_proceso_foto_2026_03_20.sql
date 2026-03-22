-- Agrega columna foto_url a ticket_procesos
ALTER TABLE ticket_procesos ADD COLUMN IF NOT EXISTS foto_url VARCHAR(500);
