"""Initial schema

Revision ID: 7643f7cc1e15
Revises: 
Create Date: 2026-04-10 11:23:57.677229-05:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7643f7cc1e15'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema.
    
    Note: This is the initial migration for an existing database.
    The schema already exists and was created by db/migracion_jwt_auth_2026_03_28.sql
    
    This migration serves as the baseline for future schema changes.
    No operations are performed as the schema is already in place.
    
    Future migrations will be generated with:
        alembic revision --autogenerate -m "Description of changes"
    """
    pass


def downgrade() -> None:
    """Downgrade schema.
    
    Note: This is the initial migration baseline.
    Downgrading from this point would require dropping all tables,
    which should be done manually if needed.
    """
    pass
