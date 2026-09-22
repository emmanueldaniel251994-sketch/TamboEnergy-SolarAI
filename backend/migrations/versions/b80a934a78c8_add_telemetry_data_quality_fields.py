"""add telemetry data quality fields

Revision ID: b80a934a78c8
Revises: b00282b62286
Create Date: 2026-09-17 14:41:23.807418
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b80a934a78c8"

down_revision: Union[
    str,
    Sequence[str],
    None
] = "b00282b62286"

branch_labels: Union[
    str,
    Sequence[str],
    None
] = None

depends_on: Union[
    str,
    Sequence[str],
    None
] = None


def upgrade() -> None:
    """Add telemetry data-quality fields safely."""

    with op.batch_alter_table(
        "telemetry",
        schema=None
    ) as batch_op:

        batch_op.add_column(
            sa.Column(
                "ml_prediction_available",
                sa.Integer(),
                nullable=False,
                server_default=sa.text("1"),
            )
        )

        batch_op.add_column(
            sa.Column(
                "data_quality_score",
                sa.Float(),
                nullable=False,
                server_default=sa.text("100.0"),
            )
        )

        batch_op.add_column(
            sa.Column(
                "missing_fields",
                sa.Text(),
                nullable=True,
            )
        )


def downgrade() -> None:
    """Remove telemetry data-quality fields."""

    with op.batch_alter_table(
        "telemetry",
        schema=None
    ) as batch_op:

        batch_op.drop_column(
            "missing_fields"
        )

        batch_op.drop_column(
            "data_quality_score"
        )

        batch_op.drop_column(
            "ml_prediction_available"
        )