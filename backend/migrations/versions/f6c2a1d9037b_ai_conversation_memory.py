"""add persistent AI conversation sessions and messages

Revision ID: f6c2a1d9037b
Revises: e3b9d421af20
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "f6c2a1d9037b"
down_revision: Union[str, Sequence[str], None] = "e3b9d421af20"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ai_conversation_sessions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("original_complaint", sa.Text(), nullable=False),
        sa.Column("equipment_profile", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_ai_conversation_sessions_user_id", "ai_conversation_sessions", ["user_id"])
    op.create_table(
        "ai_conversation_messages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("session_id", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("response_metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["ai_conversation_sessions.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_ai_conversation_messages_session_id_id", "ai_conversation_messages", ["session_id", "id"])


def downgrade() -> None:
    op.drop_index("ix_ai_conversation_messages_session_id_id", table_name="ai_conversation_messages")
    op.drop_table("ai_conversation_messages")
    op.drop_index("ix_ai_conversation_sessions_user_id", table_name="ai_conversation_sessions")
    op.drop_table("ai_conversation_sessions")
