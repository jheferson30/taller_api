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
    
    Este campo almacena el número de WhatsApp Business en formato E.164
    (ej: "+573001234567") que se usa para enrutar mensajes entrantes
    al taller correcto en un entorno multi-tenant.
    """
    op.add_column(
        'talleres',
        sa.Column(
            'whatsapp_phone_number',
            sa.String(length=50),
            nullable=True,
            comment='Número de WhatsApp Business en formato E.164 para routing de webhooks multi-tenant'
        )
    )
    
    # Crear índice único para búsquedas rápidas en el webhook router
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
