"""fix_vehiculos_unique_placa_taller

Revision ID: fix_vehiculos_placa
Revises: f71c9f49f4c0
Create Date: 2026-05-13 06:00:00.000000-05:00

Corrige el índice único de placa en vehiculos para que sea compuesto
(taller_id, placa) en lugar de solo (placa).

Sin este fix, dos talleres distintos no pueden tener el mismo número de placa,
lo que rompe el aislamiento multi-tenant.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'fix_vehiculos_placa'
down_revision: Union[str, Sequence[str], None] = 'f71c9f49f4c0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()

    # Eliminar índice único simple si existe
    if conn.execute(sa.text(
        "SELECT 1 FROM pg_indexes WHERE tablename='vehiculos' AND indexname='ix_vehiculos_placa'"
    )).fetchone():
        op.drop_index('ix_vehiculos_placa', table_name='vehiculos')

    # Crear índice único compuesto (taller_id, placa) si no existe
    if not conn.execute(sa.text(
        "SELECT 1 FROM pg_indexes WHERE tablename='vehiculos' AND indexname='uq_vehiculos_taller_placa'"
    )).fetchone():
        op.create_index(
            'uq_vehiculos_taller_placa',
            'vehiculos',
            ['taller_id', 'placa'],
            unique=True
        )


def downgrade() -> None:
    conn = op.get_bind()

    if conn.execute(sa.text(
        "SELECT 1 FROM pg_indexes WHERE tablename='vehiculos' AND indexname='uq_vehiculos_taller_placa'"
    )).fetchone():
        op.drop_index('uq_vehiculos_taller_placa', table_name='vehiculos')

    if not conn.execute(sa.text(
        "SELECT 1 FROM pg_indexes WHERE tablename='vehiculos' AND indexname='ix_vehiculos_placa'"
    )).fetchone():
        op.create_index('ix_vehiculos_placa', 'vehiculos', ['placa'], unique=True)
