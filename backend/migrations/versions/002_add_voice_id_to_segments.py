"""Add voice_id to segments

Revision ID: 002
Revises: 001
Create Date: 2026-02-02 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '002'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add voice_id column to segments table
    op.add_column('segments', sa.Column('voice_id', sa.String(length=100), nullable=True))


def downgrade() -> None:
    # Remove voice_id column from segments table
    op.drop_column('segments', 'voice_id')
