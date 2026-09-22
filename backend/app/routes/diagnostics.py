from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.telemetry import Telemetry
from app.models.solar_system import SolarSystem
from app.models.user import User

from app.security import get_current_user
from app.services.diagnostic_service import generate_diagnostic


router = APIRouter(
    prefix="/diagnostics",
    tags=["Diagnostics"],
)


@router.get("/telemetry/{telemetry_id}")
def get_telemetry_diagnostic(
    telemetry_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    # --------------------------------------------------------
    # 1. FIND TELEMETRY RECORD
    # --------------------------------------------------------

    telemetry = (
        db.query(Telemetry)
        .filter(Telemetry.id == telemetry_id)
        .first()
    )

    if not telemetry:
        raise HTTPException(
            status_code=404,
            detail="Telemetry record not found",
        )

    # --------------------------------------------------------
    # 2. FIND SOLAR SYSTEM
    # --------------------------------------------------------

    solar_system = (
        db.query(SolarSystem)
        .filter(
            SolarSystem.id == telemetry.solar_system_id
        )
        .first()
    )

    if not solar_system:
        raise HTTPException(
            status_code=404,
            detail="Solar system not found",
        )

    # --------------------------------------------------------
    # 3. CUSTOMER ACCESS CONTROL
    # --------------------------------------------------------

    if current_user.role == "customer":

        if (
            current_user.customer_id is None
            or solar_system.customer_id
            != current_user.customer_id
        ):
            raise HTTPException(
                status_code=403,
                detail=(
                    "You do not have permission to access "
                    "this diagnostic report"
                ),
            )

    # --------------------------------------------------------
    # 4. DETERMINE DIAGNOSIS
    # --------------------------------------------------------

    diagnosis = (
        telemetry.final_diagnosis
        or telemetry.fault_type
        or "normal"
    )

    # --------------------------------------------------------
    # 5. GENERATE HUMAN-READABLE DIAGNOSTIC
    # --------------------------------------------------------

    diagnostic = generate_diagnostic(
        diagnosis=diagnosis,
        severity=telemetry.fault_severity,
        confidence=telemetry.ml_confidence,
        needs_review=telemetry.needs_review,
    )

    # --------------------------------------------------------
    # 6. RETURN COMPLETE REPORT
    # --------------------------------------------------------

    return {
        "telemetry_id": telemetry.id,
        "solar_system_id": telemetry.solar_system_id,

        "diagnostic": {
            "title": diagnostic["title"],
            "diagnosis": diagnostic["diagnosis"],
            "explanation": diagnostic["explanation"],
            "possible_causes": diagnostic["possible_causes"],
            "recommended_action": diagnostic[
                "recommended_action"
            ],
            "priority": diagnostic["priority"],
        },

        "analysis": {
            "rule_prediction": (
                telemetry.fault_type or "normal"
            ),
            "rule_severity": telemetry.fault_severity,
            "ml_prediction": telemetry.ml_prediction,
            "ml_confidence": telemetry.ml_confidence,
            "prediction_agreement": (
                telemetry.prediction_agreement
            ),
            "final_diagnosis": diagnosis,
            "needs_review": telemetry.needs_review,
            "review_message": diagnostic[
                "review_message"
            ],
        },

        "telemetry": {
            "pv_voltage": telemetry.pv_voltage,
            "pv_current": telemetry.pv_current,
            "pv_power": telemetry.pv_power,
            "battery_voltage": telemetry.battery_voltage,
            "battery_current": telemetry.battery_current,
            "battery_soc": telemetry.battery_soc,
            "load_power": telemetry.load_power,
            "temperature": telemetry.temperature,
            "error_code": telemetry.error_code,
            "status": telemetry.status,
            "created_at": telemetry.created_at,
        },
    }