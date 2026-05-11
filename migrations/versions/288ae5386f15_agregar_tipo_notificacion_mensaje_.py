"""agregar_tipo_notificacion_mensaje_plataforma

Revision ID: 288ae5386f15
Revises: 0001_initial
Create Date: 2026-05-05 03:11:13.641782-05:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '288ae5386f15'
down_revision: Union[str, Sequence[str], None] = '0001_initial'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Agregar el nuevo valor al enum tiponotificacion
    op.execute("ALTER TYPE tiponotificacion ADD VALUE IF NOT EXISTS 'MENSAJE_PLATAFORMA'")


def downgrade() -> None:
    """Downgrade schema."""
    # No se puede eliminar un valor de un enum en PostgreSQL sin recrearlo
    # Por seguridad, dejamos el valor en el enum
    pass
