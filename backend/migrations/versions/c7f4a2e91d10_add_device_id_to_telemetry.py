"""add device id to telemetry

Revision ID: c7f4a2e91d10
Revises: 8c1a412bdebc
Create Date: 2026-10-01

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c7f4a2e91d10"
down_revision: Union[str, Sequence[str], None] = "8c1a412bdebc"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Attach optional device provenance to telemetry records."""
    with op.batch_alter_table("telemetry", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("device_id", sa.Integer(), nullable=True)
        )
        batch_op.create_foreign_key(
            "fk_telemetry_device_id_devices",
            "devices",
            ["device_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_index(
            batch_op.f("ix_telemetry_device_id"),
            ["device_id"],
            unique=False,
        )


def downgrade() -> None:
    """Remove telemetry device provenance."""
    with op.batch_alter_table("telemetry", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_telemetry_device_id"))
        batch_op.drop_constraint(
            "fk_telemetry_device_id_devices",
            type_="foreignkey",
        )
        batch_op.drop_column("device_id")
