"""create conversions table

Revision ID: 0001
Revises:
Create Date: 2026-08-19

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "conversions",
        sa.Column("hash", sa.String(length=64), primary_key=True),
        sa.Column("original_filename", sa.String(length=512), nullable=False),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("filename_base", sa.String(length=512), nullable=False),
        sa.Column("transcript_text", sa.Text(), nullable=False),
        sa.Column("summary_text", sa.Text(), nullable=False),
        sa.Column("whisper_model", sa.String(length=255), nullable=True),
        sa.Column("diarization_model", sa.String(length=255), nullable=True),
        sa.Column("summarization_model", sa.String(length=255), nullable=True),
        sa.Column("transcribe_seconds", sa.Float(), nullable=True),
        sa.Column("diarize_seconds", sa.Float(), nullable=True),
        sa.Column("summarize_seconds", sa.Float(), nullable=True),
        sa.Column("total_seconds", sa.Float(), nullable=True),
        sa.Column("prompt_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("completion_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_conversions_created_at", "conversions", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_conversions_created_at", table_name="conversions")
    op.drop_table("conversions")
