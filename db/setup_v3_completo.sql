-- ============================================================================
-- SETUP COMPLETO BASE DE DATOS v3 - MULTI-TENANT
-- ============================================================================
-- Este script crea la BD taller_v3 desde cero con:
--   1. Todo el esquema de la v2 (mismos lineamientos, seeds, índices)
--   2. La tabla talleres (entidad raíz del multi-tenant)
--   3. Columna taller_id en todas las tablas operativas
--   4. Índices únicos compuestos (taller_id, placa) y (taller_id, ticket_codigo)
--   5. Índices de rendimiento compuestos
--
-- USO:
--   psql -U postgres -c "CREATE DATABASE taller_v3;"
--   psql -U postgres -d taller_v3 -f db/setup_v3_completo.sql
--
-- La BD de producción (taller_db / v2) NO se toca.
-- ============================================================================

BEGIN;

-- ============================================================================
-- BLOQUE 1: ENUMS
-- (de migracion_2026_02_28.sql + migracion_cobro_rapido_2026_03_26.sql)
-- ============================================================================

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'tipomovimiento') THEN
        CREATE TYPE tipomovimiento AS ENUM (
            'INGRESO_ANTICIPO',
            'INGRESO_FINAL',
            'INGRESO_RAPIDO',
            'EGRESO'
        );
    END IF;
END$$;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'estadoticket') THEN
        CREATE TYPE estadoticket AS ENUM (
            'ABIERTO',
            'EN_PROCESO',
            'FINALIZADO',
            'ENTREGADO'
        );
    END IF;
END$$;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'categoriaegreso') THEN
        CREATE TYPE categoriaegreso AS ENUM (
            'REPUESTO',
            'PARTE',
            'INSUMO',
            'HERRAMIENTA',
            'OTRO'
        );
    END IF;
END$$;

-- ============================================================================
-- BLOQUE 2: TABLA talleres (NUEVA - entidad raíz del multi-tenant)
-- ============================================================================

CREATE TABLE IF NOT EXISTS talleres (
    id               SERIAL PRIMARY KEY,
    nombre           VARCHAR(200) UNIQUE NOT NULL,
    nit              VARCHAR(50),
    direccion        VARCHAR(300),
    telefono         VARCHAR(50),
    activo           BOOLEAN NOT NULL DEFAULT TRUE,
    fecha_creacion   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    fecha_actualizacion TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS ix_talleres_nombre ON talleres(nombre);
CREATE INDEX IF NOT EXISTS ix_talleres_activo  ON talleres(activo);

COMMENT ON TABLE talleres IS 'Entidad raíz del sistema multi-tenant. Cada taller es un tenant independiente.';

-- Insertar Taller_Default (equivalente al taller único de la v2)
INSERT INTO talleres (nombre, activo, fecha_creacion)
VALUES ('Taller Principal', TRUE, NOW())
ON CONFLICT (nombre) DO NOTHING;

-- ============================================================================
-- BLOQUE 3: TABLA users
-- (de migracion_jwt_auth_2026_03_28.sql + taller_id multi-tenant)
-- ============================================================================

CREATE TABLE IF NOT EXISTS users (
    id              SERIAL PRIMARY KEY,
    taller_id       INTEGER NOT NULL REFERENCES talleres(id),
    username        VARCHAR(50) UNIQUE NOT NULL,
    email           VARCHAR(255) UNIQUE NOT NULL,
    password_hash   VARCHAR(255) NOT NULL,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    is_migrated     BOOLEAN NOT NULL DEFAULT FALSE,
    nombre_completo VARCHAR(150),
    telefono        VARCHAR(20),
    direccion       VARCHAR(255),
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_users_username  ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_email     ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_is_active ON users(is_active);
CREATE INDEX IF NOT EXISTS ix_users_taller_id  ON users(taller_id);

COMMENT ON TABLE users IS 'Usuarios del sistema. Cada usuario pertenece a exactamente un taller.';

-- ============================================================================
-- BLOQUE 4: ROLES y USER_ROLES
-- (de migracion_jwt_auth_2026_03_28.sql)
-- ============================================================================

CREATE TABLE IF NOT EXISTS roles (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(50) UNIQUE NOT NULL,
    description VARCHAR(255),
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

INSERT INTO roles (name, description) VALUES
    ('ADMIN',        'Administrador con acceso completo al sistema'),
    ('MECANICO',     'Mecánico con acceso a tickets y procesos de reparación'),
    ('RECEPCIONISTA','Recepcionista con acceso a citas y gestión de tickets'),
    ('SOLO_LECTURA', 'Usuario con acceso de solo lectura'),
    ('SUPER_ADMIN',  'Administrador de plataforma con acceso a todos los talleres')
ON CONFLICT (name) DO NOTHING;

CREATE TABLE IF NOT EXISTS user_roles (
    user_id     INTEGER REFERENCES users(id) ON DELETE CASCADE,
    role_id     INTEGER REFERENCES roles(id) ON DELETE CASCADE,
    assigned_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (user_id, role_id)
);

-- ============================================================================
-- BLOQUE 5: TABLA vehiculos
-- (esquema v2 + taller_id + índice único compuesto)
-- ============================================================================

CREATE TABLE IF NOT EXISTS vehiculos (
    id                   SERIAL PRIMARY KEY,
    taller_id            INTEGER NOT NULL REFERENCES talleres(id),
    placa                VARCHAR(20) NOT NULL,
    marca                VARCHAR(100),
    modelo               VARCHAR(100),
    anio                 INTEGER,
    cilindraje           VARCHAR(50),
    color                VARCHAR(50),
    nombre_propietario   VARCHAR(150),
    telefono_propietario VARCHAR(20),
    fecha_creacion       TIMESTAMPTZ DEFAULT NOW(),
    fecha_actualizacion  TIMESTAMPTZ
);

-- Índice único COMPUESTO: dos talleres distintos pueden tener la misma placa
CREATE UNIQUE INDEX IF NOT EXISTS ix_vehiculos_taller_placa ON vehiculos(taller_id, placa);
CREATE INDEX IF NOT EXISTS ix_vehiculos_taller_id ON vehiculos(taller_id);

COMMENT ON TABLE vehiculos IS 'Vehículos registrados. La placa es única por taller (no globalmente).';

-- ============================================================================
-- BLOQUE 6: TABLA tickets
-- (esquema v2 + taller_id + índice único compuesto en ticket_codigo)
-- ============================================================================

CREATE TABLE IF NOT EXISTS tickets (
    id                      SERIAL PRIMARY KEY,
    taller_id               INTEGER NOT NULL REFERENCES talleres(id),
    vehiculo_id             INTEGER NOT NULL REFERENCES vehiculos(id),
    ticket_codigo           VARCHAR(40) NOT NULL,
    placa                   VARCHAR(20) NOT NULL,
    fecha_ingreso           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    motivo_visita           VARCHAR(250) NOT NULL,
    observaciones_recepcion VARCHAR(500),
    kilometraje             INTEGER,
    estado_inicial          VARCHAR(300),
    anticipo_recibido       INTEGER NOT NULL DEFAULT 0,
    metodo_pago_anticipo    VARCHAR(50),
    recepcionado_por        VARCHAR(120),
    estado                  VARCHAR(20) NOT NULL DEFAULT 'ABIERTO',
    total_servicio          INTEGER,
    saldo_pendiente         INTEGER,
    metodo_pago_final       VARCHAR(50),
    observaciones_finales   VARCHAR(800),
    recomendaciones         VARCHAR(800),
    proximo_mantenimiento   VARCHAR(200),
    confirmado_entrega_por  VARCHAR(120),
    firma_entrega_url       VARCHAR(255),
    comprobante_pdf_url     VARCHAR(255),
    fecha_cierre            TIMESTAMPTZ,
    fecha_entrega           TIMESTAMPTZ,
    fecha_actualizacion     TIMESTAMPTZ
);

-- Índice único COMPUESTO: dos talleres pueden usar el mismo código de ticket
CREATE UNIQUE INDEX IF NOT EXISTS ix_tickets_taller_codigo ON tickets(taller_id, ticket_codigo);
CREATE INDEX IF NOT EXISTS ix_tickets_vehiculo_id  ON tickets(vehiculo_id);
CREATE INDEX IF NOT EXISTS ix_tickets_placa        ON tickets(placa);
CREATE INDEX IF NOT EXISTS ix_tickets_taller_estado ON tickets(taller_id, estado);
CREATE INDEX IF NOT EXISTS ix_tickets_taller_id    ON tickets(taller_id);

COMMENT ON TABLE tickets IS 'Órdenes de servicio. ticket_codigo es único por taller (no globalmente).';

-- ============================================================================
-- BLOQUE 7: TABLAS de detalle de ticket
-- (esquema v2 + taller_id en cada una)
-- ============================================================================

CREATE TABLE IF NOT EXISTS ticket_procesos (
    id             SERIAL PRIMARY KEY,
    taller_id      INTEGER NOT NULL REFERENCES talleres(id),
    ticket_id      INTEGER NOT NULL REFERENCES tickets(id),
    nombre         VARCHAR(120) NOT NULL,
    descripcion    VARCHAR(400),
    mecanico       VARCHAR(120),
    foto_url       VARCHAR(500),
    fecha_creacion TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_ticket_procesos_ticket_id  ON ticket_procesos(ticket_id);
CREATE INDEX IF NOT EXISTS ix_ticket_procesos_taller_id  ON ticket_procesos(taller_id);

CREATE TABLE IF NOT EXISTS ticket_repuestos (
    id              SERIAL PRIMARY KEY,
    taller_id       INTEGER NOT NULL REFERENCES talleres(id),
    ticket_id       INTEGER NOT NULL REFERENCES tickets(id),
    proceso_id      INTEGER REFERENCES ticket_procesos(id),
    nombre          VARCHAR(150) NOT NULL,
    cantidad        INTEGER NOT NULL DEFAULT 1,
    marca_referencia VARCHAR(120),
    foto_url        VARCHAR(500),
    fecha_creacion  TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_ticket_repuestos_ticket_id ON ticket_repuestos(ticket_id);
CREATE INDEX IF NOT EXISTS ix_ticket_repuestos_taller_id ON ticket_repuestos(taller_id);

CREATE TABLE IF NOT EXISTS ticket_fotos (
    id             SERIAL PRIMARY KEY,
    taller_id      INTEGER NOT NULL REFERENCES talleres(id),
    ticket_id      INTEGER NOT NULL REFERENCES tickets(id),
    tipo           VARCHAR(30) NOT NULL DEFAULT 'OTRA',
    archivo_url    VARCHAR(255) NOT NULL,
    descripcion    VARCHAR(250),
    fecha_creacion TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_ticket_fotos_ticket_id ON ticket_fotos(ticket_id);
CREATE INDEX IF NOT EXISTS ix_ticket_fotos_taller_id ON ticket_fotos(taller_id);

CREATE TABLE IF NOT EXISTS ticket_compras (
    id             SERIAL PRIMARY KEY,
    taller_id      INTEGER NOT NULL REFERENCES talleres(id),
    ticket_id      INTEGER NOT NULL REFERENCES tickets(id),
    descripcion    VARCHAR(250) NOT NULL,
    valor          INTEGER NOT NULL,
    soporte_url    VARCHAR(255),
    nota           VARCHAR(500),
    responsable    VARCHAR(120),
    fecha_creacion TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_ticket_compras_ticket_id ON ticket_compras(ticket_id);
CREATE INDEX IF NOT EXISTS ix_ticket_compras_taller_id ON ticket_compras(taller_id);

CREATE TABLE IF NOT EXISTS ticket_cobros (
    id             SERIAL PRIMARY KEY,
    taller_id      INTEGER NOT NULL REFERENCES talleres(id),
    ticket_id      INTEGER NOT NULL REFERENCES tickets(id),
    concepto       VARCHAR(200) NOT NULL,
    valor          INTEGER NOT NULL,
    fecha_creacion TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_ticket_cobros_ticket_id ON ticket_cobros(ticket_id);
CREATE INDEX IF NOT EXISTS ix_ticket_cobros_taller_id ON ticket_cobros(taller_id);

-- ============================================================================
-- BLOQUE 8: TABLA movimientos_caja
-- (esquema v2 + taller_id + índice compuesto de rendimiento)
-- ============================================================================

CREATE TABLE IF NOT EXISTS movimientos_caja (
    id                  SERIAL PRIMARY KEY,
    taller_id           INTEGER NOT NULL REFERENCES talleres(id),
    tipo                tipomovimiento NOT NULL,
    ticket_id           INTEGER,
    ticket_codigo       VARCHAR(40),
    placa               VARCHAR(20),
    estado_ticket       estadoticket,
    valor               INTEGER NOT NULL,
    metodo_pago         VARCHAR(50),
    categoria_egreso    categoriaegreso,
    concepto            VARCHAR(200),
    responsable         VARCHAR(120),
    observacion         TEXT,
    soporte_url         VARCHAR(255),
    creado_por          VARCHAR(120),
    fecha_actualizacion TIMESTAMPTZ,
    fecha_creacion      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_movimientos_caja_ticket_codigo  ON movimientos_caja(ticket_codigo);
CREATE INDEX IF NOT EXISTS ix_movimientos_caja_placa          ON movimientos_caja(placa);
CREATE INDEX IF NOT EXISTS ix_movimientos_caja_ticket_id      ON movimientos_caja(ticket_id);
CREATE INDEX IF NOT EXISTS ix_movimientos_taller_fecha        ON movimientos_caja(taller_id, fecha_creacion);
CREATE INDEX IF NOT EXISTS ix_movimientos_caja_taller_id      ON movimientos_caja(taller_id);

-- ============================================================================
-- BLOQUE 9: TABLA cambios_movimiento_caja
-- (esquema v2 + taller_id)
-- ============================================================================

CREATE TABLE IF NOT EXISTS cambios_movimiento_caja (
    id                   SERIAL PRIMARY KEY,
    taller_id            INTEGER NOT NULL REFERENCES talleres(id),
    movimiento_id        INTEGER NOT NULL REFERENCES movimientos_caja(id),
    motivo               VARCHAR(200) NOT NULL,
    valor_anterior       INTEGER NOT NULL,
    valor_nuevo          INTEGER NOT NULL,
    observacion_anterior TEXT,
    observacion_nueva    TEXT,
    actualizado_por      VARCHAR(120),
    fecha_creacion       TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_cambios_movimiento_caja_movimiento_id ON cambios_movimiento_caja(movimiento_id);
CREATE INDEX IF NOT EXISTS ix_cambios_movimiento_caja_taller_id     ON cambios_movimiento_caja(taller_id);

-- ============================================================================
-- BLOQUE 10: TABLA citas
-- (de migracion_citas_2026_03_12.sql + migracion_citas_vehiculo_2026_03_13.sql + taller_id)
-- ============================================================================

CREATE TABLE IF NOT EXISTS citas (
    id                  SERIAL PRIMARY KEY,
    taller_id           INTEGER NOT NULL REFERENCES talleres(id),
    vehiculo_id         INTEGER REFERENCES vehiculos(id),
    placa               VARCHAR(20) NOT NULL,
    marca               VARCHAR(100),
    modelo              VARCHAR(100),
    anio                INTEGER,
    cilindraje          VARCHAR(50),
    color               VARCHAR(50),
    nombre_cliente      VARCHAR(150) NOT NULL,
    telefono_cliente    VARCHAR(50) NOT NULL,
    fecha_cita          TIMESTAMPTZ NOT NULL,
    motivo              VARCHAR(250) NOT NULL,
    observaciones       VARCHAR(500),
    estado              VARCHAR(20) NOT NULL DEFAULT 'PENDIENTE',
    ticket_id           INTEGER REFERENCES tickets(id),
    ticket_codigo       VARCHAR(40),
    creado_por          VARCHAR(120),
    fecha_creacion      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    fecha_actualizacion TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS ix_citas_placa     ON citas(placa);
CREATE INDEX IF NOT EXISTS ix_citas_taller_fecha ON citas(taller_id, fecha_cita);
CREATE INDEX IF NOT EXISTS ix_citas_estado    ON citas(estado);
CREATE INDEX IF NOT EXISTS ix_citas_ticket_id ON citas(ticket_id);
CREATE INDEX IF NOT EXISTS ix_citas_taller_id ON citas(taller_id);

COMMENT ON COLUMN citas.estado IS 'Estados: PENDIENTE, CONFIRMADA, CANCELADA, CONVERTIDA';

-- ============================================================================
-- BLOQUE 11: TABLA mecanicos
-- (de migracion_configuracion_2026_03_20.sql + taller_id)
-- ============================================================================

CREATE TABLE IF NOT EXISTS mecanicos (
    id        SERIAL PRIMARY KEY,
    taller_id INTEGER NOT NULL REFERENCES talleres(id),
    nombre    VARCHAR(100) NOT NULL,
    activo    BOOLEAN NOT NULL DEFAULT TRUE
);
CREATE INDEX IF NOT EXISTS ix_mecanicos_taller_id ON mecanicos(taller_id);

-- ============================================================================
-- BLOQUE 12: TABLA configuracion_taller
-- (de migracion_configuracion_2026_03_20.sql + todos los ALTER posteriores + taller_id 1:1)
-- ============================================================================

CREATE TABLE IF NOT EXISTS configuracion_taller (
    id                SERIAL PRIMARY KEY,
    taller_id         INTEGER UNIQUE NOT NULL REFERENCES talleres(id),
    nombre_taller     VARCHAR(200) NOT NULL DEFAULT 'Taller Mecánico',
    direccion         VARCHAR(300),
    telefono          VARCHAR(50),
    nit               VARCHAR(50),
    procesos_rapidos  TEXT DEFAULT '[]',
    cobros_rapidos    TEXT DEFAULT '[]',
    whatsapp_token    TEXT,
    whatsapp_phone_id VARCHAR(50),
    whatsapp_enabled  BOOLEAN NOT NULL DEFAULT FALSE,
    smtp_user         VARCHAR(200),
    smtp_password     TEXT,
    smtp_from         VARCHAR(200),
    logo_url          VARCHAR(255)
);

CREATE INDEX IF NOT EXISTS ix_configuracion_taller_taller_id ON configuracion_taller(taller_id);

-- Insertar configuración por defecto para el Taller Principal
INSERT INTO configuracion_taller (taller_id, nombre_taller, procesos_rapidos, cobros_rapidos)
SELECT id, nombre, '[]', '[]' FROM talleres WHERE nombre = 'Taller Principal'
ON CONFLICT (taller_id) DO NOTHING;

-- ============================================================================
-- BLOQUE 13: TABLA configuracion_seguridad
-- (de migracion_seguridad_2026_03_11.sql — sin taller_id, es global del sistema)
-- ============================================================================

CREATE TABLE IF NOT EXISTS configuracion_seguridad (
    id                  SERIAL PRIMARY KEY,
    clave               VARCHAR(50) UNIQUE NOT NULL,
    valor_hash          VARCHAR(255) NOT NULL,
    fecha_creacion      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    fecha_actualizacion TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_configuracion_seguridad_clave ON configuracion_seguridad(clave);

-- ============================================================================
-- BLOQUE 14: TABLAS de autenticación JWT
-- (de migracion_jwt_auth_2026_03_28.sql)
-- ============================================================================

CREATE TABLE IF NOT EXISTS audit_log (
    id            SERIAL PRIMARY KEY,
    user_id       INTEGER REFERENCES users(id) ON DELETE SET NULL,
    taller_id     INTEGER REFERENCES talleres(id) ON DELETE SET NULL,
    action        VARCHAR(50) NOT NULL,
    resource_type VARCHAR(50),
    resource_id   INTEGER,
    ip_address    VARCHAR(45) NOT NULL,
    user_agent    VARCHAR(500),
    details       JSONB,
    timestamp     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_audit_log_user_id    ON audit_log(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_taller_id  ON audit_log(taller_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_action     ON audit_log(action);
CREATE INDEX IF NOT EXISTS idx_audit_log_resource   ON audit_log(resource_type, resource_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_timestamp  ON audit_log(timestamp);
CREATE INDEX IF NOT EXISTS idx_audit_log_ip_address ON audit_log(ip_address);

CREATE TABLE IF NOT EXISTS token_blacklist (
    id             SERIAL PRIMARY KEY,
    jti            VARCHAR(36) UNIQUE NOT NULL,
    token_type     VARCHAR(20) NOT NULL,
    user_id        INTEGER REFERENCES users(id) ON DELETE CASCADE,
    expires_at     TIMESTAMPTZ NOT NULL,
    blacklisted_at TIMESTAMPTZ DEFAULT NOW(),
    reason         VARCHAR(100)
);

CREATE INDEX IF NOT EXISTS idx_token_blacklist_jti        ON token_blacklist(jti);
CREATE INDEX IF NOT EXISTS idx_token_blacklist_user_id    ON token_blacklist(user_id);
CREATE INDEX IF NOT EXISTS idx_token_blacklist_expires_at ON token_blacklist(expires_at);

CREATE TABLE IF NOT EXISTS password_reset_tokens (
    id         SERIAL PRIMARY KEY,
    user_id    INTEGER REFERENCES users(id) ON DELETE CASCADE,
    token      VARCHAR(64) UNIQUE NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    used       BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_password_reset_tokens_token      ON password_reset_tokens(token);
CREATE INDEX IF NOT EXISTS idx_password_reset_tokens_user_id    ON password_reset_tokens(user_id);
CREATE INDEX IF NOT EXISTS idx_password_reset_tokens_expires_at ON password_reset_tokens(expires_at);

-- ============================================================================
-- BLOQUE 15: TABLA log_notificacion
-- (de migracion_whatsapp_2026.sql + taller_id)
-- ============================================================================

CREATE TABLE IF NOT EXISTS log_notificacion (
    id               SERIAL PRIMARY KEY,
    taller_id        INTEGER REFERENCES talleres(id) ON DELETE SET NULL,
    ticket_id        INTEGER REFERENCES tickets(id) ON DELETE SET NULL,
    telefono_destino VARCHAR(30),
    tipo_evento      VARCHAR(20) NOT NULL,
    mensaje_enviado  TEXT,
    resultado        VARCHAR(10) NOT NULL,
    error_detalle    TEXT,
    created_at       TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_log_notificacion_ticket_id  ON log_notificacion(ticket_id);
CREATE INDEX IF NOT EXISTS idx_log_notificacion_taller_id  ON log_notificacion(taller_id);
CREATE INDEX IF NOT EXISTS idx_log_notificacion_created_at ON log_notificacion(created_at DESC);

-- ============================================================================
-- BLOQUE 16: Índice de rendimiento en movimientos_caja.fecha_creacion
-- (de migracion_jwt_auth_2026_03_28.sql)
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_movimientos_caja_fecha_creacion ON movimientos_caja(fecha_creacion);

-- ============================================================================
-- BLOQUE 17: Marcar migración Alembic como aplicada
-- (para que alembic no intente correr la migración del multi-tenant de nuevo)
-- ============================================================================

CREATE TABLE IF NOT EXISTS alembic_version (
    version_num VARCHAR(32) NOT NULL,
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);

-- Marcar ambas migraciones como ya aplicadas (initial + multi-tenant)
INSERT INTO alembic_version (version_num) VALUES ('7643f7cc1e15')
ON CONFLICT DO NOTHING;

INSERT INTO alembic_version (version_num) VALUES ('a1b2c3d4e5f6')
ON CONFLICT DO NOTHING;

-- ============================================================================
-- VERIFICACIÓN FINAL
-- ============================================================================
DO $$
BEGIN
    RAISE NOTICE '✅ BD taller_v3 creada exitosamente';
    RAISE NOTICE '   Tablas: talleres, users, roles, user_roles, vehiculos, tickets';
    RAISE NOTICE '   Tablas: ticket_procesos, ticket_repuestos, ticket_fotos, ticket_compras, ticket_cobros';
    RAISE NOTICE '   Tablas: movimientos_caja, cambios_movimiento_caja, citas, mecanicos';
    RAISE NOTICE '   Tablas: configuracion_taller, configuracion_seguridad, audit_log';
    RAISE NOTICE '   Tablas: token_blacklist, password_reset_tokens, log_notificacion';
    RAISE NOTICE '   Taller_Default insertado: Taller Principal';
    RAISE NOTICE '   Roles insertados: ADMIN, MECANICO, RECEPCIONISTA, SOLO_LECTURA, SUPER_ADMIN';
    RAISE NOTICE '   Alembic marcado en versión: a1b2c3d4e5f6 (multi-tenant completo)';
END $$;

COMMIT;
