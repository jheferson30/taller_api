"""add_mecanico_user_id_to_procesos_and_responsable_user_id_to_compras

Revision ID: f71c9f49f4c0
Revises: 4e67176cc05b
Create Date: 2026-05-11 09:00:00.000000-05:00

Agrega FK opcionales a users en ticket_procesos y ticket_compras.
Los campos string existentes (mecanico, responsable) se conservan para
compatibilidad con la app mobile.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'f71c9f49f4c0'
down_revision: Union[str, Sequence[str], None] = '4e67176cc05b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ticket_procesos: agregar mecanico_user_id FK a users
    op.add_column(
        'ticket_procesos',
        sa.Column('mecanico_user_id', sa.Integer(), nullable=True)
    )
    op.create_foreign_key(
        'fk_ticket_procesos_mecanico_user_id',
        'ticket_procesos', 'users',
        ['mecanico_user_id'], ['id'],
        ondelete='SET NULL'
    )
    op.create_index('ix_ticket_procesos_mecanico_user_id', 'ticket_procesos', ['mecanico_user_id'])

    # ticket_compras: agregar responsable_user_id FK a users
    op.add_column(
        'ticket_compras',
        sa.Column('responsable_user_id', sa.Integer(), nullable=True)
    )
    op.create_foreign_key(
        'fk_ticket_compras_responsable_user_id',
        'ticket_compras', 'users',
        ['responsable_user_id'], ['id'],
        ondelete='SET NULL'
    )
    op.create_index('ix_ticket_compras_responsable_user_id', 'ticket_compras', ['responsable_user_id'])


def downgrade() -> None:
    op.drop_index('ix_ticket_compras_responsable_user_id', table_name='ticket_compras')
    op.drop_constraint('fk_ticket_compras_responsable_user_id', 'ticket_compras', type_='foreignkey')
    op.drop_column('ticket_compras', 'responsable_user_id')

    op.drop_index('ix_ticket_procesos_mecanico_user_id', table_name='ticket_procesos')
    op.drop_constraint('fk_ticket_procesos_mecanico_user_id', 'ticket_procesos', type_='foreignkey')
    op.drop_column('ticket_procesos', 'mecanico_user_id')
