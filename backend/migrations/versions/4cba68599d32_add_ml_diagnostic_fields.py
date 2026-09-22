"""add ml diagnostic fields

Revision ID: 4cba68599d32
Revises: 401c9827c092
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# ============================================================
# ALEMBIC REVISION INFORMATION
# ============================================================

revision: str = "4cba68599d32"

down_revision: Union[
    str,
    Sequence[str],
    None
] = "401c9827c092"

branch_labels = None
depends_on = None


# ============================================================
# UPGRADE
# ============================================================

def upgrade() -> None:

    connection = op.get_bind()

    inspector = sa.inspect(
        connection
    )

    existing_columns = {
        column["name"]
        for column in inspector.get_columns(
            "telemetry"
        )
    }


    # --------------------------------------------------------
    # ML prediction
    # --------------------------------------------------------

    if "ml_prediction" not in existing_columns:

        op.add_column(
            "telemetry",
            sa.Column(
                "ml_prediction",
                sa.String(),
                nullable=True
            )
        )


    # --------------------------------------------------------
    # ML confidence
    # --------------------------------------------------------

    if "ml_confidence" not in existing_columns:

        op.add_column(
            "telemetry",
            sa.Column(
                "ml_confidence",
                sa.Float(),
                nullable=True
            )
        )


    # --------------------------------------------------------
    # Prediction agreement
    # --------------------------------------------------------

    if "prediction_agreement" not in existing_columns:

        op.add_column(
            "telemetry",
            sa.Column(
                "prediction_agreement",
                sa.String(),
                nullable=True
            )
        )


    # --------------------------------------------------------
    # Final diagnosis
    # --------------------------------------------------------

    if "final_diagnosis" not in existing_columns:

        op.add_column(
            "telemetry",
            sa.Column(
                "final_diagnosis",
                sa.String(),
                nullable=True
            )
        )


    # --------------------------------------------------------
    # Needs technician review
    #
    # server_default=0 is important because existing
    # telemetry rows need a value.
    # --------------------------------------------------------

    if "needs_review" not in existing_columns:

        op.add_column(
            "telemetry",
            sa.Column(
                "needs_review",
                sa.Integer(),
                nullable=False,
                server_default=sa.text("0")
            )
        )


# ============================================================
# DOWNGRADE
# ============================================================

def downgrade() -> None:

    connection = op.get_bind()

    inspector = sa.inspect(
        connection
    )

    existing_columns = {
        column["name"]
        for column in inspector.get_columns(
            "telemetry"
        )
    }


    with op.batch_alter_table(
        "telemetry",
        schema=None
    ) as batch_op:

        if "needs_review" in existing_columns:
            batch_op.drop_column(
                "needs_review"
            )

        if "final_diagnosis" in existing_columns:
            batch_op.drop_column(
                "final_diagnosis"
            )

        if "prediction_agreement" in existing_columns:
            batch_op.drop_column(
                "prediction_agreement"
            )

        if "ml_confidence" in existing_columns:
            batch_op.drop_column(
                "ml_confidence"
            )

        if "ml_prediction" in existing_columns:
            batch_op.drop_column(
                "ml_prediction"
            )