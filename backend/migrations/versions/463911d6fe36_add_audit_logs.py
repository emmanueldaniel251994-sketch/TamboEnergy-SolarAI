"""add audit logs

Revision ID: 463911d6fe36
Revises: c0b2563a1dd6
Create Date: 2026-09-08

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "463911d6fe36"

down_revision: Union[str, Sequence[str], None] = "c0b2563a1dd6"

branch_labels: Union[str, Sequence[str], None] = None

depends_on: Union[str, Sequence[str], None] = None


# ============================================================
# UPGRADE
# ============================================================

def upgrade() -> None:

    # Create audit_logs table
    op.create_table(
        "audit_logs",

        sa.Column(
            "id",
            sa.Integer(),
            nullable=False
        ),

        sa.Column(
            "user_id",
            sa.Integer(),
            nullable=True
        ),

        sa.Column(
            "action",
            sa.String(),
            nullable=False
        ),

        sa.Column(
            "resource_type",
            sa.String(),
            nullable=False
        ),

        sa.Column(
            "resource_id",
            sa.Integer(),
            nullable=True
        ),

        sa.Column(
            "details",
            sa.Text(),
            nullable=True
        ),

        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False
        ),

        sa.PrimaryKeyConstraint(
            "id",
            name="pk_audit_logs"
        ),

        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_audit_logs_user_id_users",
            ondelete="SET NULL"
        )
    )


    # Index for id
    op.create_index(
        "ix_audit_logs_id",
        "audit_logs",
        ["id"],
        unique=False
    )


    # Index for user_id
    op.create_index(
        "ix_audit_logs_user_id",
        "audit_logs",
        ["user_id"],
        unique=False
    )


    # Index for action
    op.create_index(
        "ix_audit_logs_action",
        "audit_logs",
        ["action"],
        unique=False
    )


    # Index for resource_type
    op.create_index(
        "ix_audit_logs_resource_type",
        "audit_logs",
        ["resource_type"],
        unique=False
    )


    # Index for resource_id
    op.create_index(
        "ix_audit_logs_resource_id",
        "audit_logs",
        ["resource_id"],
        unique=False
    )


# ============================================================
# DOWNGRADE
# ============================================================

def downgrade() -> None:

    op.drop_index(
        "ix_audit_logs_resource_id",
        table_name="audit_logs"
    )

    op.drop_index(
        "ix_audit_logs_resource_type",
        table_name="audit_logs"
    )

    op.drop_index(
        "ix_audit_logs_action",
        table_name="audit_logs"
    )

    op.drop_index(
        "ix_audit_logs_user_id",
        table_name="audit_logs"
    )

    op.drop_index(
        "ix_audit_logs_id",
        table_name="audit_logs"
    )

    op.drop_table(
        "audit_logs"
    )