from sqlalchemy.orm import Session

from app.models.alert import Alert
from app.services.diagnostic_service import generate_diagnostic


ALERT_PRIORITIES = {
    "medium",
    "high",
    "critical",
}


def create_fault_alert(
    db: Session,
    telemetry,
):
    """
    Create an alert from a telemetry record.

    Priority:
    1. Actual detected fault
    2. Rule/ML disagreement
    3. Poor telemetry data quality

    Existing active alerts of the same type are not duplicated.
    """

    diagnosis = (
        telemetry.final_diagnosis
        or telemetry.fault_type
        or "normal"
    )

    diagnostic = generate_diagnostic(
        diagnosis=diagnosis,
        severity=telemetry.fault_severity,
        confidence=telemetry.ml_confidence,
        needs_review=telemetry.needs_review,
    )

    priority = diagnostic["priority"]

    # ========================================================
    # CASE 1 — ACTUAL FAULT / WARNING
    # ========================================================
    #
    # A real deterministic fault has priority over
    # ML disagreement or poor data quality.
    # ========================================================

    if (
        diagnosis != "normal"
        and priority in ALERT_PRIORITIES
    ):
        alert_type = diagnosis
        severity = priority
        title = diagnostic["title"]

        message = (
            f"{diagnostic['explanation']} "
            f"{diagnostic['recommended_action']}"
        )

        if (
            telemetry.ml_prediction_available == 0
        ):
            message += (
                " ML analysis was unavailable because "
                "the telemetry record was incomplete."
            )

        elif (
            telemetry.prediction_agreement
            == "disagree"
        ):
            message += (
                " The rule engine and ML model "
                "produced different diagnoses. "
                "Technician review is recommended."
            )

    # ========================================================
    # CASE 2 — RULE / ML DISAGREEMENT
    # ========================================================

    elif (
        telemetry.prediction_agreement
        == "disagree"
    ):
        alert_type = "diagnosis_disagreement"
        severity = "medium"

        title = (
            "SolarAI diagnosis requires technician review"
        )

        message = (
            f"Rule-based diagnosis: "
            f"{telemetry.fault_type or 'normal'}. "
            f"ML prediction: "
            f"{telemetry.ml_prediction or 'unknown'}. "
            f"Final diagnosis: {diagnosis}. "
            f"Technician review is recommended."
        )

    # ========================================================
    # CASE 3 — POOR / INCOMPLETE TELEMETRY
    # ========================================================

    elif (
        telemetry.ml_prediction_available == 0
    ):
        alert_type = "data_quality"
        severity = "medium"

        title = (
            "Incomplete solar telemetry detected"
        )

        missing = (
            telemetry.missing_fields
            or "unknown fields"
        )

        message = (
            f"Telemetry data quality is "
            f"{telemetry.data_quality_score}%. "
            f"Missing fields: {missing}. "
            f"ML diagnosis was disabled because "
            f"there was not enough sensor data. "
            f"Check the telemetry source, inverter "
            f"communication, gateway, or sensors."
        )

    # ========================================================
    # CASE 4 — NOTHING REQUIRES AN ALERT
    # ========================================================

    else:
        return None

    # ========================================================
    # ALERT DEDUPLICATION
    # ========================================================

    existing_alert = (
        db.query(Alert)
        .filter(
            Alert.solar_system_id
            == telemetry.solar_system_id,

            Alert.alert_type
            == alert_type,

            Alert.status.in_(
                [
                    "open",
                    "acknowledged",
                ]
            ),
        )
        .order_by(
            Alert.created_at.desc()
        )
        .first()
    )

    if existing_alert:
        return existing_alert

    # ========================================================
    # CREATE ALERT
    # ========================================================

    new_alert = Alert(
        solar_system_id=(
            telemetry.solar_system_id
        ),

        telemetry_id=(
            telemetry.id
        ),

        alert_type=alert_type,

        severity=severity,

        title=title,

        message=message,

        status="open",

        needs_review=(
            telemetry.needs_review
        ),
    )

    db.add(new_alert)
    db.flush()

    return new_alert