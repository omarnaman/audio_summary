"""make summary_text nullable so transcripts can be persisted before summarization

Revision ID: 0002
Revises: 0001
Create Date: 2026-08-20

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("conversions", "summary_text", existing_type=sa.Text(), nullable=True)


def downgrade() -> None:
    op.alter_column("conversions", "summary_text", existing_type=sa.Text(), nullable=False)
