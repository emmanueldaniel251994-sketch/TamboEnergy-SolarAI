from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
)

from sqlalchemy.orm import Session

from app.database import get_db

from app.models.telemetry import Telemetry
from app.models.solar_system import SolarSystem
from app.models.alert import Alert
from app.models.user import User


from app.schemas.telemetry import (
    TelemetryCreate,
    TelemetryResponse,
)

from app.security import (
    get_current_user,
    require_roles,
)

from app.services.audit import log_action

from app.services.fault_detection import (
    detect_fault,
)

from app.services.ml_prediction import (
    predict_fault,
)

from app.services.alert_service import (
    create_fault_alert,
)

from app.services.data_quality import (
    assess_data_quality,
)


router = APIRouter(
    prefix="/telemetry",
    tags=["Telemetry"],
)


# ============================================================
# SAFETY-CRITICAL RULES
# ============================================================
#
# ML must never override these deterministic safety
# conditions when the rule engine detects them.
# ============================================================

SAFETY_CRITICAL_RULES = {
    "critical_low_battery",
    "battery_undervoltage",
    "battery_overvoltage",
    "high_temperature",
    "overheating",
    "high_load",
    "inverter_error",
}


# ============================================================
# CREATE TELEMETRY
# ============================================================

@router.post(
    "/",
    response_model=TelemetryResponse,
)
def create_telemetry(
    telemetry: TelemetryCreate,

    db: Session = Depends(
        get_db
    ),

    current_user: User = Depends(
        require_roles(
            "admin",
            "technician",
        )
    ),
):

    # ========================================================
    # CHECK SOLAR SYSTEM
    # ========================================================

    solar_system = (
        db.query(SolarSystem)
        .filter(
            SolarSystem.id
            == telemetry.solar_system_id
        )
        .first()
    )

    if not solar_system:
        raise HTTPException(
            status_code=404,
            detail="Solar system not found",
        )

    # ========================================================
    # CALCULATE PV POWER
    # ========================================================
    #
    # If PV power was not supplied but both voltage and
    # current are available:
    #
    # P = V × I
    #
    # Important:
    # If current is missing, PV power remains None.
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
    # DATA QUALITY ASSESSMENT
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

    data_quality_score = (
        quality_result[
            "data_quality_score"
        ]
    )

    missing_fields_list = (
        quality_result[
            "missing_fields"
        ]
    )

    ml_prediction_available = (
        quality_result[
            "ml_prediction_available"
        ]
    )

    # Store the list in SQLite as comma-separated text.
    if missing_fields_list:
        missing_fields = ",".join(
            missing_fields_list
        )
    else:
        missing_fields = None

    # ========================================================
    # RULE-BASED FAULT DETECTION
    # ========================================================
    #
    # The rule engine can still work with available sensor
    # measurements even when other fields are missing.
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
        fault_result.get(
            "fault_type"
        )
        or "normal"
    )

    rule_severity = (
        fault_result.get(
            "fault_severity"
        )
        or "none"
    )

    detected_status = (
        fault_result.get(
            "status"
        )
        or "normal"
    )

    # ========================================================
    # MACHINE LEARNING PREDICTION
    # ========================================================
    #
    # ML is only used when enough sensor information exists.
    #
    # This prevents missing values from being converted to
    # zero and accidentally creating a false diagnosis.
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

        # The ML service itself may still fail safely.
        if ml_result.get(
            "prediction_available",
            True,
        ):

            ml_prediction = (
                ml_result.get(
                    "predicted_fault"
                )
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

    # --------------------------------------------------------
    # CASE 1:
    # ML NOT AVAILABLE
    # --------------------------------------------------------
    #
    # The deterministic rule engine remains active.
    #
    # We do not call this an ML disagreement because ML was
    # never trusted/run.
    # --------------------------------------------------------

    if not ml_prediction_available:

        prediction_agreement = (
            "not_available"
        )

        final_diagnosis = (
            rule_prediction
        )

        needs_review = 1

    # --------------------------------------------------------
    # CASE 2:
    # RULE ENGINE AND ML AGREE
    # --------------------------------------------------------

    elif rule_prediction == ml_prediction:

        prediction_agreement = "agree"

        final_diagnosis = (
            rule_prediction
        )

        needs_review = 0

    # --------------------------------------------------------
    # CASE 3:
    # RULE ENGINE AND ML DISAGREE
    # --------------------------------------------------------

    else:

        prediction_agreement = (
            "disagree"
        )

        needs_review = 1

        # ----------------------------------------------------
        # SAFETY RULE PRIORITY
        # ----------------------------------------------------
        #
        # ML cannot override deterministic critical/high
        # electrical or safety conditions.
        # ----------------------------------------------------

        if (
            rule_prediction
            in SAFETY_CRITICAL_RULES
        ):

            final_diagnosis = (
                rule_prediction
            )

        # ----------------------------------------------------
        # NON-SAFETY DISAGREEMENT
        # ----------------------------------------------------
        #
        # A high-confidence ML prediction may assist when
        # there is no deterministic safety rule.
        # Technician review is still required.
        # ----------------------------------------------------

        elif ml_confidence >= 0.90:

            final_diagnosis = (
                ml_prediction
            )

        else:

            final_diagnosis = (
                rule_prediction
            )

    # ========================================================
    # CREATE TELEMETRY DATABASE RECORD
    # ========================================================

    new_record = Telemetry(

        solar_system_id=(
            telemetry.solar_system_id
        ),

        pv_voltage=(
            telemetry.pv_voltage
        ),

        pv_current=(
            telemetry.pv_current
        ),

        pv_power=(
            pv_power
        ),

        battery_voltage=(
            telemetry.battery_voltage
        ),

        battery_current=(
            telemetry.battery_current
        ),

        battery_soc=(
            telemetry.battery_soc
        ),

        load_power=(
            telemetry.load_power
        ),

        temperature=(
            telemetry.temperature
        ),

        error_code=(
            telemetry.error_code
        ),

        # Rule engine result
        fault_type=(
            rule_prediction
        ),

        fault_severity=(
            rule_severity
        ),

        # ML result
        ml_prediction=(
            ml_prediction
        ),

        ml_confidence=(
            ml_confidence
        ),

        ml_prediction_available=(
            ml_prediction_available
        ),

        # Data quality
        data_quality_score=(
            data_quality_score
        ),

        missing_fields=(
            missing_fields
        ),

        # Combined diagnosis
        prediction_agreement=(
            prediction_agreement
        ),

        final_diagnosis=(
            final_diagnosis
        ),

        needs_review=(
            needs_review
        ),

        # Do not trust incoming status.
        # Store the rule engine's detected status.
        status=(
            detected_status
        ),
    )

    db.add(
        new_record
    )

    # Flush first so the telemetry record receives its ID.
    db.flush()

    # ========================================================
    # AUTOMATIC ALERT CREATION
    # ========================================================

    create_fault_alert(
        db=db,
        telemetry=new_record,
    )

    # ========================================================
    # AUDIT LOG
    # ========================================================

    log_action(
        db=db,

        user_id=current_user.id,

        action="create",

        resource_type="telemetry",

        resource_id=new_record.id,

        details=(
            f"Telemetry created for solar system "
            f"{telemetry.solar_system_id}. "
            f"Data quality: "
            f"{data_quality_score}%. "
            f"ML available: "
            f"{ml_prediction_available}. "
            f"Rule diagnosis: "
            f"{rule_prediction}. "
            f"ML prediction: "
            f"{ml_prediction}. "
            f"Final diagnosis: "
            f"{final_diagnosis}. "
            f"Needs review: "
            f"{needs_review}."
        ),
    )

    # ========================================================
    # SAVE DATABASE TRANSACTION
    # ========================================================

    db.commit()

    db.refresh(
        new_record
    )

    return new_record


# ============================================================
# GET TELEMETRY
# ============================================================

@router.get(
    "/",
    response_model=list[TelemetryResponse],
)
def get_telemetry(

    solar_system_id: int | None = None,

    limit: int = 100,

    db: Session = Depends(
        get_db
    ),

    current_user: User = Depends(
        get_current_user
    ),
):

    # Limit maximum number of records returned.
    limit = max(
        1,
        min(
            limit,
            500,
        ),
    )

    query = db.query(
        Telemetry
    )

    # ========================================================
    # CUSTOMER ACCESS CONTROL
    # ========================================================

    if current_user.role == "customer":

        if (
            current_user.customer_id
            is None
        ):
            return []

        customer_system_ids = [
            system.id

            for system in (
                db.query(
                    SolarSystem
                )
                .filter(
                    SolarSystem.customer_id
                    == current_user.customer_id
                )
                .all()
            )
        ]

        if not customer_system_ids:
            return []

        query = query.filter(
            Telemetry.solar_system_id.in_(
                customer_system_ids
            )
        )

    # ========================================================
    # OPTIONAL SOLAR SYSTEM FILTER
    # ========================================================

    if solar_system_id is not None:

        if (
            current_user.role
            == "customer"
        ):

            solar_system = (
                db.query(
                    SolarSystem
                )
                .filter(
                    SolarSystem.id
                    == solar_system_id
                )
                .first()
            )

            if not solar_system:

                raise HTTPException(
                    status_code=404,
                    detail=(
                        "Solar system not found"
                    ),
                )

            if (
                solar_system.customer_id
                != current_user.customer_id
            ):

                raise HTTPException(
                    status_code=403,
                    detail=(
                        "You do not have permission "
                        "to access this solar system"
                    ),
                )

        query = query.filter(
            Telemetry.solar_system_id
            == solar_system_id
        )

    records = (
        query
        .order_by(
            Telemetry.created_at.desc()
        )
        .limit(
            limit
        )
        .all()
    )

    return records


# ============================================================
# GET LATEST TELEMETRY
# ============================================================

@router.get(
    "/latest/{solar_system_id}",
    response_model=TelemetryResponse,
)
def get_latest_telemetry(

    solar_system_id: int,

    db: Session = Depends(
        get_db
    ),

    current_user: User = Depends(
        get_current_user
    ),
):

    # ========================================================
    # CHECK SOLAR SYSTEM
    # ========================================================

    solar_system = (
        db.query(
            SolarSystem
        )
        .filter(
            SolarSystem.id
            == solar_system_id
        )
        .first()
    )

    if not solar_system:

        raise HTTPException(
            status_code=404,
            detail=(
                "Solar system not found"
            ),
        )

    # ========================================================
    # CUSTOMER OWNERSHIP CHECK
    # ========================================================

    if (
        current_user.role
        == "customer"
    ):

        if (
            current_user.customer_id
            is None

            or solar_system.customer_id
            != current_user.customer_id
        ):

            raise HTTPException(
                status_code=403,
                detail=(
                    "You do not have permission "
                    "to access this solar system"
                ),
            )

    # ========================================================
    # GET LATEST TELEMETRY RECORD
    # ========================================================

    latest_record = (
        db.query(
            Telemetry
        )
        .filter(
            Telemetry.solar_system_id
            == solar_system_id
        )
        .order_by(
            Telemetry.created_at.desc()
        )
        .first()
    )

    if not latest_record:

        raise HTTPException(
            status_code=404,
            detail=(
                "No telemetry found for "
                "this solar system"
            ),
        )

    return latest_record
# ============================================================
# DELETE TELEMETRY / DIAGNOSTIC
# Admin Only
# ============================================================

@router.delete("/{telemetry_id}")
def delete_telemetry(
    telemetry_id: int,

    db: Session = Depends(
        get_db
    ),

    current_user: User = Depends(
        require_roles("admin")
    ),
):
    """
    Permanently delete a telemetry record and the diagnostic
    information generated from that telemetry.

    Only administrators are allowed to perform this action.

    Any alerts directly linked to the telemetry record are
    deleted first.
    """

    # ========================================================
    # FIND TELEMETRY RECORD
    # ========================================================

    telemetry_record = (
        db.query(Telemetry)
        .filter(
            Telemetry.id == telemetry_id
        )
        .first()
    )

    if not telemetry_record:
        raise HTTPException(
            status_code=404,
            detail="Telemetry record not found",
        )

    # Save important information before deletion.
    solar_system_id = (
        telemetry_record.solar_system_id
    )

    try:

        # ====================================================
        # FIND LINKED ALERTS
        # ====================================================

        linked_alerts = (
            db.query(Alert)
            .filter(
                Alert.telemetry_id == telemetry_id
            )
            .all()
        )

        deleted_alert_ids = [
            alert.id
            for alert in linked_alerts
        ]

        # ====================================================
        # DELETE LINKED ALERTS
        # ====================================================
        #
        # Alert.telemetry_id currently uses ON DELETE CASCADE.
        #
        # We still delete linked alerts explicitly here so the
        # application behaviour is clear and predictable rather
        # than depending only on database cascade behaviour.
        # ====================================================

        for alert in linked_alerts:
            db.delete(alert)

        # Flush alert deletions before deleting telemetry.
        db.flush()

        # ====================================================
        # AUDIT LOG
        # ====================================================

        log_action(
            db=db,

            user_id=current_user.id,

            action="DELETE_TELEMETRY",

            resource_type="telemetry",

            resource_id=telemetry_id,

            details=(
                f"Telemetry {telemetry_id} permanently deleted "
                f"for solar system {solar_system_id}. "
                f"Linked alerts deleted: "
                f"{deleted_alert_ids}."
            ),
        )

        # ====================================================
        # DELETE TELEMETRY
        # ====================================================

        db.delete(
            telemetry_record
        )

        # ====================================================
        # SAVE TRANSACTION
        # ====================================================

        db.commit()

        # ====================================================
        # RESPONSE
        # ====================================================

        return {
            "message": (
                "Telemetry and diagnostic "
                "deleted successfully"
            ),
            "telemetry_id": telemetry_id,
            "solar_system_id": solar_system_id,
            "deleted_alert_ids": (
                deleted_alert_ids
            ),
        }

    except HTTPException:

        db.rollback()

        raise

    except Exception as error:

        db.rollback()

        # Log the actual error in the backend terminal
        # without exposing internal database information
        # to the frontend.
        print(
            f"Delete telemetry error: {error}"
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "Unable to delete telemetry record."
            ),
        )