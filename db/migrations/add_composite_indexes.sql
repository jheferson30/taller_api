-- Migración: Índices Compuestos para Optimización de Base de Datos
-- Fecha: 2026-04-06
-- Propósito: Agregar índices compuestos para optimizar consultas frecuentes
-- Requirements: 2.10, 2.11, 2.14

-- Índice compuesto para consultas de tickets por estado y fecha
-- Optimiza: SELECT * FROM tickets WHERE estado = 'ABIERTO' AND fecha_ingreso >= '...' ORDER BY fecha_ingreso DESC
CREATE INDEX IF NOT EXISTS idx_tickets_estado_fecha 
ON tickets(estado, fecha_ingreso DESC);

-- Índice para búsqueda rápida por placa
-- Optimiza: SELECT * FROM tickets WHERE placa = '...'
CREATE INDEX IF NOT EXISTS idx_tickets_placa 
ON tickets(placa);

-- Índice compuesto para audit_log por usuario, acción y fecha
-- Optimiza: SELECT * FROM audit_log WHERE user_id = ... AND action = '...' ORDER BY timestamp DESC
CREATE INDEX IF NOT EXISTS idx_audit_log_user_action_date 
ON audit_log(user_id, action, timestamp DESC);

-- Índice compuesto para token blacklist por jti y expiración
-- Optimiza: SELECT * FROM token_blacklist WHERE jti = '...' AND expires_at > NOW()
CREATE INDEX IF NOT EXISTS idx_token_blacklist_jti_exp 
ON token_blacklist(jti, expires_at);

-- Índice para búsqueda rápida de vehículos por placa
-- Optimiza: SELECT * FROM vehiculos WHERE placa = '...'
CREATE INDEX IF NOT EXISTS idx_vehiculos_placa 
ON vehiculos(placa);
