BEGIN;

-- ==============================
-- 1) ENUMS
-- ==============================
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'tipomovimiento') THEN
        CREATE TYPE tipomovimiento AS ENUM ('INGRESO_ANTICIPO', 'INGRESO_FINAL', 'EGRESO');
    END IF;
END$$;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'estadoticket') THEN
        CREATE TYPE estadoticket AS ENUM ('ABIERTO', 'EN_PROCESO', 'FINALIZADO', 'ENTREGADO');
    END IF;
END$$;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'categoriaegreso') THEN
        CREATE TYPE categoriaegreso AS ENUM ('REPUESTO', 'PARTE', 'INSUMO', 'HERRAMIENTA', 'OTRO');
    END IF;
END$$;

DO $$
BEGIN
    -- Compatibilidad si el enum ya existia sin EN_PROCESO/ENTREGADO.
    IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'estadoticket') THEN
        BEGIN
            ALTER TYPE estadoticket ADD VALUE IF NOT EXISTS 'EN_PROCESO';
        EXCEPTION WHEN duplicate_object THEN NULL;
        END;
        BEGIN
            ALTER TYPE estadoticket ADD VALUE IF NOT EXISTS 'ENTREGADO';
        EXCEPTION WHEN duplicate_object THEN NULL;
        END;
    END IF;
END$$;

-- ==============================
-- 2) VEHICULOS
-- ==============================
ALTER TABLE IF EXISTS vehiculos
    ALTER COLUMN nombre_propietario DROP NOT NULL,
    ALTER COLUMN telefono_propietario DROP NOT NULL;

-- ==============================
-- 3) MOVIMIENTOS DE CAJA
-- ==============================
ALTER TABLE IF EXISTS movimientos_caja
    ADD COLUMN IF NOT EXISTS ticket_codigo VARCHAR(40),
    ADD COLUMN IF NOT EXISTS placa VARCHAR(20),
    ADD COLUMN IF NOT EXISTS estado_ticket estadoticket,
    ADD COLUMN IF NOT EXISTS categoria_egreso categoriaegreso,
    ADD COLUMN IF NOT EXISTS concepto VARCHAR(200),
    ADD COLUMN IF NOT EXISTS responsable VARCHAR(120),
    ADD COLUMN IF NOT EXISTS observacion TEXT,
    ADD COLUMN IF NOT EXISTS soporte_url VARCHAR(255),
    ADD COLUMN IF NOT EXISTS creado_por VARCHAR(120),
    ADD COLUMN IF NOT EXISTS fecha_actualizacion TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS ix_movimientos_caja_ticket_codigo ON movimientos_caja(ticket_codigo);
CREATE INDEX IF NOT EXISTS ix_movimientos_caja_placa ON movimientos_caja(placa);
CREATE INDEX IF NOT EXISTS ix_movimientos_caja_ticket_id ON movimientos_caja(ticket_id);

-- ==============================
-- 4) TICKETS
-- ==============================
CREATE TABLE IF NOT EXISTS tickets (
    id SERIAL PRIMARY KEY,
    vehiculo_id INTEGER NOT NULL REFERENCES vehiculos(id),
    ticket_codigo VARCHAR(40) NOT NULL UNIQUE,
    placa VARCHAR(20) NOT NULL,
    fecha_ingreso TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    motivo_visita VARCHAR(250) NOT NULL,
    observaciones_recepcion VARCHAR(500),
    kilometraje INTEGER,
    estado_inicial VARCHAR(300),
    anticipo_recibido INTEGER NOT NULL DEFAULT 0,
    metodo_pago_anticipo VARCHAR(50),
    recepcionado_por VARCHAR(120),
    estado VARCHAR(20) NOT NULL DEFAULT 'ABIERTO',
    total_servicio INTEGER,
    saldo_pendiente INTEGER,
    metodo_pago_final VARCHAR(50),
    observaciones_finales VARCHAR(800),
    recomendaciones VARCHAR(800),
    proximo_mantenimiento VARCHAR(200),
    confirmado_entrega_por VARCHAR(120),
    firma_entrega_url VARCHAR(255),
    comprobante_pdf_url VARCHAR(255),
    fecha_cierre TIMESTAMPTZ,
    fecha_entrega TIMESTAMPTZ,
    fecha_actualizacion TIMESTAMPTZ
);

ALTER TABLE IF EXISTS tickets
    ADD COLUMN IF NOT EXISTS total_servicio INTEGER,
    ADD COLUMN IF NOT EXISTS saldo_pendiente INTEGER,
    ADD COLUMN IF NOT EXISTS metodo_pago_final VARCHAR(50),
    ADD COLUMN IF NOT EXISTS observaciones_finales VARCHAR(800),
    ADD COLUMN IF NOT EXISTS recomendaciones VARCHAR(800),
    ADD COLUMN IF NOT EXISTS proximo_mantenimiento VARCHAR(200),
    ADD COLUMN IF NOT EXISTS confirmado_entrega_por VARCHAR(120),
    ADD COLUMN IF NOT EXISTS firma_entrega_url VARCHAR(255),
    ADD COLUMN IF NOT EXISTS comprobante_pdf_url VARCHAR(255),
    ADD COLUMN IF NOT EXISTS fecha_entrega TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS fecha_actualizacion TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS ix_tickets_vehiculo_id ON tickets(vehiculo_id);
CREATE INDEX IF NOT EXISTS ix_tickets_ticket_codigo ON tickets(ticket_codigo);
CREATE INDEX IF NOT EXISTS ix_tickets_placa ON tickets(placa);
CREATE INDEX IF NOT EXISTS ix_tickets_estado ON tickets(estado);

-- ==============================
-- 5) TICKET PROCESOS / REPUESTOS / FOTOS / COMPRAS
-- ==============================
CREATE TABLE IF NOT EXISTS ticket_procesos (
    id SERIAL PRIMARY KEY,
    ticket_id INTEGER NOT NULL REFERENCES tickets(id),
    nombre VARCHAR(120) NOT NULL,
    descripcion VARCHAR(400),
    mecanico VARCHAR(120),
    fecha_creacion TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_ticket_procesos_ticket_id ON ticket_procesos(ticket_id);

CREATE TABLE IF NOT EXISTS ticket_repuestos (
    id SERIAL PRIMARY KEY,
    ticket_id INTEGER NOT NULL REFERENCES tickets(id),
    proceso_id INTEGER REFERENCES ticket_procesos(id),
    nombre VARCHAR(150) NOT NULL,
    cantidad INTEGER NOT NULL DEFAULT 1,
    marca_referencia VARCHAR(120),
    fecha_creacion TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_ticket_repuestos_ticket_id ON ticket_repuestos(ticket_id);
CREATE INDEX IF NOT EXISTS ix_ticket_repuestos_proceso_id ON ticket_repuestos(proceso_id);

CREATE TABLE IF NOT EXISTS ticket_fotos (
    id SERIAL PRIMARY KEY,
    ticket_id INTEGER NOT NULL REFERENCES tickets(id),
    tipo VARCHAR(30) NOT NULL DEFAULT 'OTRA',
    archivo_url VARCHAR(255) NOT NULL,
    descripcion VARCHAR(250),
    fecha_creacion TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_ticket_fotos_ticket_id ON ticket_fotos(ticket_id);

CREATE TABLE IF NOT EXISTS ticket_compras (
    id SERIAL PRIMARY KEY,
    ticket_id INTEGER NOT NULL REFERENCES tickets(id),
    descripcion VARCHAR(250) NOT NULL,
    valor INTEGER NOT NULL,
    soporte_url VARCHAR(255),
    nota VARCHAR(500),
    responsable VARCHAR(120),
    fecha_creacion TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_ticket_compras_ticket_id ON ticket_compras(ticket_id);

-- ==============================
-- 6) AUDITORIA DE CORRECCIONES EN CAJA
-- ==============================
CREATE TABLE IF NOT EXISTS cambios_movimiento_caja (
    id SERIAL PRIMARY KEY,
    movimiento_id INTEGER NOT NULL REFERENCES movimientos_caja(id),
    motivo VARCHAR(200) NOT NULL,
    valor_anterior INTEGER NOT NULL,
    valor_nuevo INTEGER NOT NULL,
    observacion_anterior TEXT,
    observacion_nueva TEXT,
    actualizado_por VARCHAR(120),
    fecha_creacion TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_cambios_movimiento_caja_movimiento_id ON cambios_movimiento_caja(movimiento_id);

COMMIT;
