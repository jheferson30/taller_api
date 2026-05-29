"""add_metodo_pago_to_ticket_cobros

Revision ID: a2b3c4d5e6f7
Revises: ff8a2acf80d3
Create Date: 2026-05-29 10:00:00.000000

Agrega columna metodo_pago a ticket_cobros para registrar el método de pago
de cada cobro parcial y permitir que aparezca correctamente en Economía del Día.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'a2b3c4d5e6f7'
down_revision: Union[str, Sequence[str], None] = 'ff8a2acf80d3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'ticket_cobros',
        sa.Column('metodo_pago', sa.String(50), nullable=True)
    )


def downgrade() -> None:
    op.drop_column('ticket_cobros', 'metodo_pago')
