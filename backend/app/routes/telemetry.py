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

from app.services.telemetry_processor import (
    process_telemetry,
)


router = APIRouter(
    prefix="/telemetry",
    tags=["Telemetry"],
)


# ============================================================
# CREATE TELEMETRY
# Admin + Technician
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

    try:

        # ====================================================
        # SHARED SOLARAI TELEMETRY PIPELINE
        # ====================================================

        new_record = process_telemetry(
            db=db,
            telemetry=telemetry,
        )

        # ====================================================
        # AUDIT LOG
        # ====================================================

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
                f"{new_record.data_quality_score}%. "
                f"ML available: "
                f"{new_record.ml_prediction_available}. "
                f"Rule diagnosis: "
                f"{new_record.fault_type}. "
                f"ML prediction: "
                f"{new_record.ml_prediction}. "
                f"Final diagnosis: "
                f"{new_record.final_diagnosis}. "
                f"Needs review: "
                f"{new_record.needs_review}."
            ),
        )

        # ====================================================
        # SAVE TRANSACTION
        # ====================================================

        db.commit()
        db.refresh(new_record)

        return new_record

    except HTTPException:

        db.rollback()
        raise

    except Exception as error:

        db.rollback()

        print(
            f"Create telemetry error: {error}"
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "Unable to create telemetry record."
            ),
        )


# ============================================================
# GET TELEMETRY
# ============================================================

@router.get(
    "/",
    response_model=list[TelemetryResponse],
)
def get_telemetry(
    solar_system_id: int | None = None,
    device_id: int | None = None,
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
    # OPTIONAL DEVICE FILTER
    # ========================================================

    if device_id is not None:
        query = query.filter(
            Telemetry.device_id == device_id
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
                Alert.telemetry_id
                == telemetry_id
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

        for alert in linked_alerts:
            db.delete(alert)

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

        print(
            f"Delete telemetry error: {error}"
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "Unable to delete telemetry record."
            ),
        )