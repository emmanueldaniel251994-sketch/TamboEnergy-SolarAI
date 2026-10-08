"""harden device ingestion

Revision ID: e3b9d421af20
Revises: c7f4a2e91d10
Create Date: 2026-10-05

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e3b9d421af20"
down_revision: Union[str, Sequence[str], None] = "c7f4a2e91d10"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("telemetry", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("device_event_id", sa.String(length=100), nullable=True)
        )
        batch_op.add_column(
            sa.Column("device_timestamp", sa.DateTime(timezone=True), nullable=True)
        )
        batch_op.create_index(
            batch_op.f("ix_telemetry_device_event_id"),
            ["device_event_id"],
            unique=False,
        )
        batch_op.create_index(
            batch_op.f("ix_telemetry_device_timestamp"),
            ["device_timestamp"],
            unique=False,
        )
        batch_op.create_unique_constraint(
            "uq_telemetry_device_event",
            ["device_id", "device_event_id"],
        )

    op.create_table(
        "device_request_nonces",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("device_id", sa.Integer(), nullable=False),
        sa.Column("nonce", sa.String(length=128), nullable=False),
        sa.Column("request_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["device_id"],
            ["devices.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "device_id",
            "nonce",
            name="uq_device_request_nonce_device_nonce",
        ),
    )
    op.create_index(
        op.f("ix_device_request_nonces_id"),
        "device_request_nonces",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_device_request_nonces_device_id"),
        "device_request_nonces",
        ["device_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_device_request_nonces_created_at"),
        "device_request_nonces",
        ["created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_device_request_nonces_created_at"),
        table_name="device_request_nonces",
    )
    op.drop_index(
        op.f("ix_device_request_nonces_device_id"),
        table_name="device_request_nonces",
    )
    op.drop_index(
        op.f("ix_device_request_nonces_id"),
        table_name="device_request_nonces",
    )
    op.drop_table("device_request_nonces")

    with op.batch_alter_table("telemetry", schema=None) as batch_op:
        batch_op.drop_constraint("uq_telemetry_device_event", type_="unique")
        batch_op.drop_index(batch_op.f("ix_telemetry_device_timestamp"))
        batch_op.drop_index(batch_op.f("ix_telemetry_device_event_id"))
        batch_op.drop_column("device_timestamp")
        batch_op.drop_column("device_event_id")
