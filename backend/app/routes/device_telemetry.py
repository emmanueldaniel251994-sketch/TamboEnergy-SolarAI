from datetime import datetime, timezone

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
)

from sqlalchemy.orm import Session

from app.database import get_db

from app.models.device import Device
from app.models.solar_system import SolarSystem

from app.schemas.device_telemetry import (
    DeviceTelemetryCreate,
)

from app.schemas.telemetry import (
    TelemetryCreate,
    TelemetryResponse,
)

from app.device_auth import (
    get_current_device,
)

from app.services.telemetry_processor import (
    process_telemetry,
)

from app.services.audit import (
    log_action,
)


router = APIRouter(
    prefix="/device-telemetry",
    tags=["Device Telemetry"],
)


@router.post(
    "/",
    response_model=TelemetryResponse,
)
def ingest_device_telemetry(
    payload: DeviceTelemetryCreate,

    db: Session = Depends(
        get_db
    ),

    device: Device = Depends(
        get_current_device
    ),
):
    """
    Receive telemetry from an authenticated
    SolarAI monitoring device.
    """

    # ========================================================
    # VERIFY LINKED SOLAR SYSTEM
    # ========================================================

    solar_system = (
        db.query(SolarSystem)
        .filter(
            SolarSystem.id
            == device.solar_system_id
        )
        .first()
    )

    if not solar_system:
        raise HTTPException(
            status_code=404,
            detail=(
                "Solar system linked to device "
                "was not found"
            ),
        )

    try:

        # ====================================================
        # BUILD INTERNAL TELEMETRY OBJECT
        # ====================================================
        #
        # The solar system ID comes from the authenticated
        # device, never from the incoming request.
        # ====================================================

        telemetry = TelemetryCreate(
            solar_system_id=(
                device.solar_system_id
            ),

            pv_voltage=payload.pv_voltage,
            pv_current=payload.pv_current,
            pv_power=payload.pv_power,

            battery_voltage=(
                payload.battery_voltage
            ),

            battery_current=(
                payload.battery_current
            ),

            battery_soc=payload.battery_soc,

            load_power=payload.load_power,

            temperature=payload.temperature,

            error_code=payload.error_code,
        )

        # ====================================================
        # RUN SHARED SOLARAI PIPELINE
        # ====================================================

        new_record = process_telemetry(
            db=db,
            telemetry=telemetry,
        )

        # ====================================================
        # UPDATE DEVICE LAST-SEEN TIME
        # ====================================================

        device.last_seen = datetime.now(
            timezone.utc
        )

        # ====================================================
        # AUDIT LOG
        # ====================================================
        #
        # Device telemetry has no human user.
        # audit.user_id therefore remains None.
        # ====================================================

        log_action(
            db=db,
            user_id=None,
            action="device_telemetry",
            resource_type="telemetry",
            resource_id=new_record.id,
            details=(
                f"Telemetry received from device "
                f"{device.id} "
                f"({device.device_name}) "
                f"for solar system "
                f"{device.solar_system_id}. "
                f"Data quality: "
                f"{new_record.data_quality_score}%. "
                f"Final diagnosis: "
                f"{new_record.final_diagnosis}."
            ),
        )

        # ====================================================
        # COMMIT EVERYTHING AS ONE TRANSACTION
        # ====================================================

        db.commit()

        db.refresh(new_record)
        db.refresh(device)

        return new_record

    except HTTPException:

        db.rollback()
        raise

    except Exception as error:

        db.rollback()

        print(
            f"Device telemetry error: {error}"
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "Unable to process device telemetry."
            ),
        )