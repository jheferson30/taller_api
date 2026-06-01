"""merge_security_migrations

Revision ID: ff8a2acf80d3
Revises: 7643f7cc1e15, a1b2c3d4e5f6, c05_whatsapp_routing
Create Date: 2026-05-09 10:58:00.437864-05:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ff8a2acf80d3'
down_revision: Union[str, Sequence[str], None] = ('7643f7cc1e15', 'a1b2c3d4e5f6', 'c05_whatsapp_routing')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
