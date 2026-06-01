"""add_whatsapp_phone_number_to_talleres

Revision ID: c05_whatsapp_routing
Revises: 288ae5386f15
Create Date: 2026-05-05 10:00:00.000000-05:00

Agrega el campo whatsapp_phone_number a la tabla talleres para
implementar routing multi-tenant de webhooks de WhatsApp.

Resolves: C-05 (Webhook routing incorrecto para multi-taller)
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c05_whatsapp_routing'
down_revision: Union[str, Sequence[str], None] = '288ae5386f15'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Agrega el campo whatsapp_phone_number a la tabla talleres.
    Usa IF NOT EXISTS para ser idempotente si el schema inicial ya lo incluye.
    """
    # Verificar si la columna ya existe antes de agregarla
    conn = op.get_bind()
    result = conn.execute(sa.text(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_name='talleres' AND column_name='whatsapp_phone_number'"
    ))
    if result.fetchone() is None:
        op.add_column(
            'talleres',
            sa.Column(
                'whatsapp_phone_number',
                sa.String(length=50),
                nullable=True,
                comment='Número de WhatsApp Business en formato E.164 para routing de webhooks multi-tenant'
            )
        )

    # Crear índice único si no existe
    result2 = conn.execute(sa.text(
        "SELECT indexname FROM pg_indexes "
        "WHERE tablename='talleres' AND indexname='ix_talleres_whatsapp_phone_number'"
    ))
    if result2.fetchone() is None:
        op.create_index(
            'ix_talleres_whatsapp_phone_number',
            'talleres',
            ['whatsapp_phone_number'],
            unique=True
        )


def downgrade() -> None:
    """
    Elimina el campo whatsapp_phone_number de la tabla talleres.
    """
    op.drop_index('ix_talleres_whatsapp_phone_number', table_name='talleres')
    op.drop_column('talleres', 'whatsapp_phone_number')
