-- Migración: agregar foto_url a ticket_repuestos
ALTER TABLE ticket_repuestos ADD COLUMN IF NOT EXISTS foto_url VARCHAR(500);
