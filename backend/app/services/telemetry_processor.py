from sqlalchemy.orm import Session

from app.models.telemetry import Telemetry
from app.schemas.telemetry import TelemetryCreate

from app.services.fault_detection import detect_fault
from app.services.ml_prediction import predict_fault
from app.services.alert_service import create_fault_alert
from app.services.data_quality import assess_data_quality


SAFETY_CRITICAL_RULES = {
    "critical_low_battery",
    "battery_undervoltage",
    "battery_overvoltage",
    "high_temperature",
    "overheating",
    "high_load",
    "inverter_error",
}


def process_telemetry(
    db: Session,
    telemetry: TelemetryCreate,
) -> Telemetry:
    """
    Process and store telemetry through the common
    SolarAI diagnostic pipeline.

    This function does not commit the transaction.
    The calling route controls the final commit.
    """

    # ========================================================
    # CALCULATE PV POWER
    # ========================================================

    pv_power = telemetry.pv_power

    if (
        pv_power is None
        and telemetry.pv_voltage is not None
        and telemetry.pv_current is not None
    ):
        pv_power = (
            telemetry.pv_voltage
            * telemetry.pv_current
        )

    # ========================================================
    # DATA QUALITY
    # ========================================================

    quality_result = assess_data_quality(
        pv_voltage=telemetry.pv_voltage,
        pv_current=telemetry.pv_current,
        pv_power=pv_power,
        battery_voltage=telemetry.battery_voltage,
        battery_current=telemetry.battery_current,
        battery_soc=telemetry.battery_soc,
        load_power=telemetry.load_power,
        temperature=telemetry.temperature,
    )

    data_quality_score = quality_result[
        "data_quality_score"
    ]

    missing_fields_list = quality_result[
        "missing_fields"
    ]

    ml_prediction_available = quality_result[
        "ml_prediction_available"
    ]

    if missing_fields_list:
        missing_fields = ",".join(
            missing_fields_list
        )
    else:
        missing_fields = None

    # ========================================================
    # RULE-BASED DIAGNOSIS
    # ========================================================

    fault_result = detect_fault(
        pv_voltage=telemetry.pv_voltage,
        pv_current=telemetry.pv_current,
        pv_power=pv_power,
        battery_voltage=telemetry.battery_voltage,
        battery_current=telemetry.battery_current,
        battery_soc=telemetry.battery_soc,
        load_power=telemetry.load_power,
        temperature=telemetry.temperature,
        error_code=telemetry.error_code,
    )

    rule_prediction = (
        fault_result.get("fault_type")
        or "normal"
    )

    rule_severity = (
        fault_result.get("fault_severity")
        or "none"
    )

    detected_status = (
        fault_result.get("status")
        or "normal"
    )

    # ========================================================
    # MACHINE LEARNING
    # ========================================================

    if ml_prediction_available:

        ml_result = predict_fault(
            pv_voltage=telemetry.pv_voltage,
            pv_current=telemetry.pv_current,
            pv_power=pv_power,
            battery_voltage=telemetry.battery_voltage,
            battery_current=telemetry.battery_current,
            battery_soc=telemetry.battery_soc,
            load_power=telemetry.load_power,
            temperature=telemetry.temperature,
            error_code=telemetry.error_code,
        )

        if ml_result.get(
            "prediction_available",
            True,
        ):
            ml_prediction = ml_result.get(
                "predicted_fault"
            )

            ml_confidence = float(
                ml_result.get(
                    "confidence",
                    0.0,
                )
            )

        else:
            ml_prediction_available = 0
            ml_prediction = None
            ml_confidence = 0.0

    else:
        ml_prediction = None
        ml_confidence = 0.0

    # ========================================================
    # RULE + ML DECISION ENGINE
    # ========================================================

    if not ml_prediction_available:

        prediction_agreement = "not_available"
        final_diagnosis = rule_prediction
        needs_review = 1

    elif rule_prediction == ml_prediction:

        prediction_agreement = "agree"
        final_diagnosis = rule_prediction
        needs_review = 0

    else:

        prediction_agreement = "disagree"
        needs_review = 1

        if (
            rule_prediction
            in SAFETY_CRITICAL_RULES
        ):
            final_diagnosis = rule_prediction

        elif ml_confidence >= 0.90:
            final_diagnosis = ml_prediction

        else:
            final_diagnosis = rule_prediction

    # ========================================================
    # CREATE TELEMETRY RECORD
    # ========================================================

    new_record = Telemetry(
        solar_system_id=telemetry.solar_system_id,

        pv_voltage=telemetry.pv_voltage,
        pv_current=telemetry.pv_current,
        pv_power=pv_power,

        battery_voltage=telemetry.battery_voltage,
        battery_current=telemetry.battery_current,
        battery_soc=telemetry.battery_soc,

        load_power=telemetry.load_power,
        temperature=telemetry.temperature,
        error_code=telemetry.error_code,

        fault_type=rule_prediction,
        fault_severity=rule_severity,

        ml_prediction=ml_prediction,
        ml_confidence=ml_confidence,
        ml_prediction_available=(
            ml_prediction_available
        ),

        data_quality_score=data_quality_score,
        missing_fields=missing_fields,

        prediction_agreement=(
            prediction_agreement
        ),

        final_diagnosis=final_diagnosis,
        needs_review=needs_review,

        # Incoming status is deliberately ignored.
        status=detected_status,
    )

    db.add(new_record)

    # We need the telemetry ID before alert creation.
    db.flush()

    # ========================================================
    # AUTOMATIC ALERT CREATION
    # ========================================================

    create_fault_alert(
        db=db,
        telemetry=new_record,
    )

    return new_record