"""add_asignado_a_user_id_to_tickets

Revision ID: 4e67176cc05b
Revises: ff8a2acf80d3
Create Date: 2026-05-11 02:11:51.957205-05:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4e67176cc05b'
down_revision: Union[str, Sequence[str], None] = 'ff8a2acf80d3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Agrega asignado_a_user_id a tickets para asignación de usuario del taller."""
    op.add_column(
        'tickets',
        sa.Column('asignado_a_user_id', sa.Integer(), nullable=True)
    )
    op.create_foreign_key(
        'fk_tickets_asignado_a_user_id',
        'tickets', 'users',
        ['asignado_a_user_id'], ['id'],
        ondelete='SET NULL'
    )
    op.create_index('ix_tickets_asignado_a_user_id', 'tickets', ['asignado_a_user_id'])


def downgrade() -> None:
    """Revierte la columna asignado_a_user_id."""
    op.drop_index('ix_tickets_asignado_a_user_id', table_name='tickets')
    op.drop_constraint('fk_tickets_asignado_a_user_id', 'tickets', type_='foreignkey')
    op.drop_column('tickets', 'asignado_a_user_id')
