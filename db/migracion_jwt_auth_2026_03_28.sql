-- Migración: Sistema de Autenticación JWT y Auditoría
-- Fecha: 2026-03-28
-- Descripción: Crea tablas para autenticación JWT, roles, auditoría y gestión de tokens
-- Requirements: 14.1, 14.2, 15.1, 20.1, 12.5

-- ============================================================================
-- TABLA: users
-- Descripción: Almacena usuarios del sistema con contraseñas hasheadas
-- ============================================================================
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    is_migrated BOOLEAN DEFAULT FALSE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE
);

-- Índices para users
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_is_active ON users(is_active);

COMMENT ON TABLE users IS 'Usuarios del sistema con autenticación JWT';
COMMENT ON COLUMN users.username IS 'Nombre de usuario único';
COMMENT ON COLUMN users.email IS 'Email único del usuario';
COMMENT ON COLUMN users.password_hash IS 'Hash de contraseña (bcrypt o argon2)';
COMMENT ON COLUMN users.is_active IS 'Indica si el usuario está activo';
COMMENT ON COLUMN users.is_migrated IS 'Flag temporal para migración de SHA256 a bcrypt';

-- ============================================================================
-- TABLA: roles
-- Descripción: Define roles del sistema (ADMIN, MECANICO, etc.)
-- ============================================================================
CREATE TABLE IF NOT EXISTS roles (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL,
    description VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

COMMENT ON TABLE roles IS 'Roles del sistema para control de acceso';
COMMENT ON COLUMN roles.name IS 'Nombre único del rol';
COMMENT ON COLUMN roles.description IS 'Descripción del rol y sus permisos';

-- Insertar roles por defecto
INSERT INTO roles (name, description) VALUES
    ('ADMIN', 'Administrador con acceso completo al sistema'),
    ('MECANICO', 'Mecánico con acceso a tickets y procesos de reparación'),
    ('RECEPCIONISTA', 'Recepcionista con acceso a citas y gestión de tickets'),
    ('SOLO_LECTURA', 'Usuario con acceso de solo lectura a información del sistema')
ON CONFLICT (name) DO NOTHING;

-- ============================================================================
-- TABLA: user_roles
-- Descripción: Relación many-to-many entre usuarios y roles
-- ============================================================================
CREATE TABLE IF NOT EXISTS user_roles (
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    role_id INTEGER REFERENCES roles(id) ON DELETE CASCADE,
    assigned_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    PRIMARY KEY (user_id, role_id)
);

COMMENT ON TABLE user_roles IS 'Relación many-to-many entre usuarios y roles';
COMMENT ON COLUMN user_roles.assigned_at IS 'Fecha y hora de asignación del rol';

-- ============================================================================
-- TABLA: audit_log
-- Descripción: Registro inmutable de todas las acciones del sistema
-- ============================================================================
CREATE TABLE IF NOT EXISTS audit_log (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    action VARCHAR(50) NOT NULL,
    resource_type VARCHAR(50),
    resource_id INTEGER,
    ip_address VARCHAR(45) NOT NULL,
    user_agent VARCHAR(500),
    details JSONB,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

-- Índices para audit_log
CREATE INDEX IF NOT EXISTS idx_audit_log_user_id ON audit_log(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_action ON audit_log(action);
CREATE INDEX IF NOT EXISTS idx_audit_log_resource ON audit_log(resource_type, resource_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_timestamp ON audit_log(timestamp);
CREATE INDEX IF NOT EXISTS idx_audit_log_ip_address ON audit_log(ip_address);

COMMENT ON TABLE audit_log IS 'Registro inmutable de auditoría de todas las acciones del sistema';
COMMENT ON COLUMN audit_log.user_id IS 'ID del usuario que realizó la acción (NULL para eventos anónimos)';
COMMENT ON COLUMN audit_log.action IS 'Tipo de acción (LOGIN, LOGOUT, CREATE, UPDATE, DELETE, etc.)';
COMMENT ON COLUMN audit_log.resource_type IS 'Tipo de recurso afectado (ticket, user, cita, etc.)';
COMMENT ON COLUMN audit_log.resource_id IS 'ID del recurso afectado';
COMMENT ON COLUMN audit_log.ip_address IS 'Dirección IP del cliente (IPv4 o IPv6)';
COMMENT ON COLUMN audit_log.user_agent IS 'User agent del cliente';
COMMENT ON COLUMN audit_log.details IS 'Información adicional en formato JSON';
COMMENT ON COLUMN audit_log.timestamp IS 'Fecha y hora del evento';

-- ============================================================================
-- TABLA: token_blacklist
-- Descripción: Lista negra de tokens JWT invalidados
-- ============================================================================
CREATE TABLE IF NOT EXISTS token_blacklist (
    id SERIAL PRIMARY KEY,
    jti VARCHAR(36) UNIQUE NOT NULL,
    token_type VARCHAR(20) NOT NULL,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    blacklisted_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    reason VARCHAR(100)
);

-- Índices para token_blacklist
CREATE INDEX IF NOT EXISTS idx_token_blacklist_jti ON token_blacklist(jti);
CREATE INDEX IF NOT EXISTS idx_token_blacklist_user_id ON token_blacklist(user_id);
CREATE INDEX IF NOT EXISTS idx_token_blacklist_expires_at ON token_blacklist(expires_at);

COMMENT ON TABLE token_blacklist IS 'Lista negra de tokens JWT invalidados (logout, usuario desactivado, etc.)';
COMMENT ON COLUMN token_blacklist.jti IS 'JWT ID único del token (UUID)';
COMMENT ON COLUMN token_blacklist.token_type IS 'Tipo de token (refresh, access)';
COMMENT ON COLUMN token_blacklist.user_id IS 'ID del usuario propietario del token';
COMMENT ON COLUMN token_blacklist.expires_at IS 'Fecha de expiración del token';
COMMENT ON COLUMN token_blacklist.blacklisted_at IS 'Fecha y hora de invalidación';
COMMENT ON COLUMN token_blacklist.reason IS 'Razón de invalidación (logout, user_deactivated, etc.)';

-- ============================================================================
-- TABLA: password_reset_tokens
-- Descripción: Tokens de recuperación de contraseña
-- ============================================================================
CREATE TABLE IF NOT EXISTS password_reset_tokens (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    token VARCHAR(64) UNIQUE NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    used BOOLEAN DEFAULT FALSE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Índices para password_reset_tokens
CREATE INDEX IF NOT EXISTS idx_password_reset_tokens_token ON password_reset_tokens(token);
CREATE INDEX IF NOT EXISTS idx_password_reset_tokens_user_id ON password_reset_tokens(user_id);
CREATE INDEX IF NOT EXISTS idx_password_reset_tokens_expires_at ON password_reset_tokens(expires_at);

COMMENT ON TABLE password_reset_tokens IS 'Tokens de recuperación de contraseña con expiración de 1 hora';
COMMENT ON COLUMN password_reset_tokens.user_id IS 'ID del usuario que solicitó el reset';
COMMENT ON COLUMN password_reset_tokens.token IS 'Token único de recuperación (SHA256 hash)';
COMMENT ON COLUMN password_reset_tokens.expires_at IS 'Fecha de expiración del token (1 hora)';
COMMENT ON COLUMN password_reset_tokens.used IS 'Indica si el token ya fue usado';
COMMENT ON COLUMN password_reset_tokens.created_at IS 'Fecha de creación del token';

-- ============================================================================
-- MEJORA: Índice en movimientos_caja.fecha_creacion
-- Descripción: Optimiza consultas de histórico económico
-- Requirement: 12.5
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_movimientos_caja_fecha_creacion 
ON movimientos_caja(fecha_creacion);

COMMENT ON INDEX idx_movimientos_caja_fecha_creacion IS 'Optimiza consultas de histórico económico por fecha';

-- ============================================================================
-- VERIFICACIÓN DE MIGRACIÓN
-- ============================================================================
DO $$
BEGIN
    RAISE NOTICE 'Migración JWT Auth completada exitosamente';
    RAISE NOTICE 'Tablas creadas: users, roles, user_roles, audit_log, token_blacklist, password_reset_tokens';
    RAISE NOTICE 'Roles insertados: ADMIN, MECANICO, RECEPCIONISTA, SOLO_LECTURA';
    RAISE NOTICE 'Índice agregado: idx_movimientos_caja_fecha_creacion';
END $$;
