from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.device_auth import AuthenticatedDevice, get_current_device
from app.models.solar_system import SolarSystem
from app.models.telemetry import Telemetry
from app.schemas.device_telemetry import DeviceTelemetryCreate
from app.schemas.telemetry import TelemetryCreate, TelemetryResponse
from app.services.audit import log_action
from app.services.device_ingestion_security import (
    enforce_device_rate_limit,
    reserve_device_nonce,
    verify_device_request,
)
from app.services.telemetry_processor import process_telemetry


router = APIRouter(prefix="/device-telemetry", tags=["Device Telemetry"])


@router.post("/", response_model=TelemetryResponse)
def ingest_device_telemetry(
    payload: DeviceTelemetryCreate,
    db: Session = Depends(get_db),
    auth: AuthenticatedDevice = Depends(get_current_device),
):
    """Receive authenticated, optionally signed telemetry from a gateway."""

    device = auth.device
    solar_system = (
        db.query(SolarSystem)
        .filter(SolarSystem.id == device.solar_system_id)
        .first()
    )
    if not solar_system:
        raise HTTPException(
            status_code=404,
            detail="Solar system linked to device was not found",
        )

    signed_payload = payload.model_dump(mode="json", exclude_unset=True)

    try:
        request_time = verify_device_request(
            api_key=auth.api_key,
            request_timestamp=auth.request_timestamp,
            nonce=auth.nonce,
            signature=auth.signature,
            payload=signed_payload,
        )

        reserve_device_nonce(
            db=db,
            device_id=device.id,
            nonce=auth.nonce,
            request_timestamp=request_time,
        )

        # A retry with a new nonce but the same event ID is idempotent and
        # should succeed even when the device is otherwise at its rate limit.
        if payload.event_id:
            existing = (
                db.query(Telemetry)
                .filter(
                    Telemetry.device_id == device.id,
                    Telemetry.device_event_id == payload.event_id,
                )
                .first()
            )
            if existing:
                device.last_seen = datetime.now(timezone.utc)
                db.commit()
                db.refresh(existing)
                return existing

        enforce_device_rate_limit(db=db, device_id=device.id)

        telemetry = TelemetryCreate(
            solar_system_id=device.solar_system_id,
            pv_voltage=payload.pv_voltage,
            pv_current=payload.pv_current,
            pv_power=payload.pv_power,
            battery_voltage=payload.battery_voltage,
            battery_current=payload.battery_current,
            battery_soc=payload.battery_soc,
            load_power=payload.load_power,
            temperature=payload.temperature,
            error_code=payload.error_code,
        )

        new_record = process_telemetry(
            db=db,
            telemetry=telemetry,
            device_id=device.id,
            device_event_id=payload.event_id,
            device_timestamp=request_time,
        )

        device.last_seen = datetime.now(timezone.utc)

        log_action(
            db=db,
            user_id=None,
            action="device_telemetry",
            resource_type="telemetry",
            resource_id=new_record.id,
            details=(
                f"Telemetry received from device {device.id} "
                f"({device.device_name}) for solar system "
                f"{device.solar_system_id}. Data quality: "
                f"{new_record.data_quality_score}%. Final diagnosis: "
                f"{new_record.final_diagnosis}."
            ),
        )

        db.commit()
        db.refresh(new_record)
        db.refresh(device)
        return new_record

    except HTTPException:
        db.rollback()
        raise
    except Exception as error:
        db.rollback()
        print(f"Device telemetry error: {error}")
        raise HTTPException(
            status_code=500,
            detail="Unable to process device telemetry.",
        )
