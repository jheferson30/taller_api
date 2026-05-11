"""Initial complete schema with multi-tenant support

Revision ID: 0001_initial
Revises: 
Create Date: 2026-04-30 00:00:00.000000-05:00

Esta es la migración inicial consolidada que crea todas las tablas del sistema
directamente desde los modelos SQLAlchemy actuales, incluyendo:

- Sistema multi-tenant (tabla talleres + taller_id en todas las tablas)
- Campos de super admin (estado, bloqueo de emergencia, etc.)
- Sistema de notificaciones
- Todas las tablas operativas del taller

Esta migración reemplaza las migraciones anteriores:
- 7643f7cc1e15_initial_schema.py
- a1b2c3d4e5f6_add_multi_tenant_taller_id.py
- b2c3d4e5f6a7_super_admin_fields.py
- c3d4e5f6a7b8_add_notificaciones_mecanico_asignado.py
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision: str = '0001_initial'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Crea todas las tablas del sistema usando los modelos SQLAlchemy actuales.
    
    Esta migración es idempotente: si las tablas ya existen, no hace nada.
    Esto permite que funcione tanto en bases de datos nuevas como existentes.
    """
    # Importar Base y todos los modelos
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    
    from app.configuracion.base_datos import Base, engine
    from app.modelos import (
        user, taller, configuracion_taller, ticket, vehiculo, cita,
        movimiento_caja, mecanico, ticket_repuesto, ticket_proceso,
        ticket_cobro, ticket_compra, ticket_foto, cambio_movimiento_caja,
        log_notificacion, audit_log, notificacion
    )
    
    # Verificar qué tablas ya existen
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())
    
    # Crear todas las tablas que no existen
    Base.metadata.create_all(bind=engine, checkfirst=True)
    
    # Insertar Taller_Default si la tabla talleres está vacía
    conn = op.get_bind()
    result = conn.execute(sa.text("SELECT COUNT(*) FROM talleres"))
    count = result.scalar()
    
    if count == 0:
        conn.execute(
            sa.text(
                "INSERT INTO talleres (nombre, activo, estado, bloqueado_emergencia, fecha_creacion) "
                "VALUES ('Taller Principal', TRUE, 'ACTIVO', FALSE, NOW())"
            )
        )
        print("✅ Taller_Default creado")
    else:
        print(f"ℹ️  Ya existen {count} talleres, no se crea Taller_Default")


def downgrade() -> None:
    """
    Elimina todas las tablas del sistema.
    
    ADVERTENCIA: Esta operación es destructiva y eliminará todos los datos.
    """
    # Eliminar tablas en orden inverso de dependencias
    tables_to_drop = [
        'notificaciones',
        'log_notificacion',
        'cambios_movimiento_caja',
        'ticket_fotos',
        'ticket_compras',
        'ticket_cobros',
        'ticket_procesos',
        'ticket_repuestos',
        'tickets',
        'citas',
        'movimientos_caja',
        'mecanicos',
        'vehiculos',
        'audit_log',
        'configuracion_taller',
        'users',
        'roles',
        'talleres',
    ]
    
    for table in tables_to_drop:
        op.execute(f'DROP TABLE IF EXISTS {table} CASCADE')
    
    # Eliminar tipos enum
    op.execute('DROP TYPE IF EXISTS tiponotificacion CASCADE')
    op.execute('DROP TYPE IF EXISTS estadotaller CASCADE')
    op.execute('DROP TYPE IF EXISTS auditaction CASCADE')
