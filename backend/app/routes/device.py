from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
)

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db

from app.models.device import Device
from app.models.solar_system import SolarSystem
from app.models.user import User

from app.schemas.device import (
    DeviceCreate,
    DeviceUpdate,
    DeviceResponse,
    DeviceRegistrationResponse,
)

from app.security import (
    get_current_user,
    require_roles,
)

from app.device_security import (
    generate_device_api_key,
    hash_device_api_key,
)

from app.services.audit import log_action


router = APIRouter(
    prefix="/devices",
    tags=["Devices"],
)


# ============================================================
# REGISTER DEVICE
# ADMIN + TECHNICIAN
# ============================================================

@router.post(
    "/",
    response_model=DeviceRegistrationResponse,
    status_code=201,
)
def register_device(
    device: DeviceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(
            "admin",
            "technician",
        )
    ),
):
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
            detail="Solar system not found",
        )

    if device.serial_number:
        existing_serial = (
            db.query(Device)
            .filter(
                Device.serial_number
                == device.serial_number
            )
            .first()
        )

        if existing_serial:
            raise HTTPException(
                status_code=409,
                detail=(
                    "A device with this serial "
                    "number already exists"
                ),
            )

    raw_api_key = generate_device_api_key()

    new_device = Device(
        solar_system_id=device.solar_system_id,
        device_name=device.device_name,
        device_type=device.device_type,
        manufacturer=device.manufacturer,
        model=device.model,
        serial_number=device.serial_number,
        api_key_hash=hash_device_api_key(
            raw_api_key
        ),
        is_active=True,
    )

    try:
        db.add(new_device)
        db.flush()

        log_action(
            db=db,
            user_id=current_user.id,
            action="create",
            resource_type="device",
            resource_id=new_device.id,
            details=(
                f"Registered device "
                f"{new_device.device_name} "
                f"for solar system "
                f"{new_device.solar_system_id}"
            ),
        )

        db.commit()
        db.refresh(new_device)

    except IntegrityError:
        db.rollback()

        raise HTTPException(
            status_code=409,
            detail=(
                "Device could not be registered "
                "because a unique value already exists"
            ),
        )

    return DeviceRegistrationResponse(
        id=new_device.id,
        solar_system_id=new_device.solar_system_id,
        device_name=new_device.device_name,
        device_type=new_device.device_type,
        manufacturer=new_device.manufacturer,
        model=new_device.model,
        serial_number=new_device.serial_number,
        is_active=new_device.is_active,
        last_seen=new_device.last_seen,
        created_at=new_device.created_at,
        api_key=raw_api_key,
    )


# ============================================================
# GET DEVICES
# AUTHENTICATED USERS
# ============================================================

@router.get(
    "/",
    response_model=list[DeviceResponse],
)
def get_devices(
    db: Session = Depends(get_db),
    current_user: User = Depends(
        get_current_user
    ),
):
    query = db.query(Device)

    if current_user.role in {
        "admin",
        "technician",
    }:
        return (
            query
            .order_by(Device.id.desc())
            .all()
        )

    if current_user.role == "customer":
        if not current_user.customer_id:
            return []

        return (
            query
            .join(
                SolarSystem,
                Device.solar_system_id
                == SolarSystem.id,
            )
            .filter(
                SolarSystem.customer_id
                == current_user.customer_id
            )
            .order_by(Device.id.desc())
            .all()
        )

    raise HTTPException(
        status_code=403,
        detail="Access denied",
    )


# ============================================================
# GET ONE DEVICE
# AUTHENTICATED USERS
# ============================================================

@router.get(
    "/{device_id}",
    response_model=DeviceResponse,
)
def get_device(
    device_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        get_current_user
    ),
):
    device = (
        db.query(Device)
        .filter(Device.id == device_id)
        .first()
    )

    if not device:
        raise HTTPException(
            status_code=404,
            detail="Device not found",
        )

    if current_user.role == "customer":
        solar_system = (
            db.query(SolarSystem)
            .filter(
                SolarSystem.id
                == device.solar_system_id
            )
            .first()
        )

        if (
            not solar_system
            or solar_system.customer_id
            != current_user.customer_id
        ):
            raise HTTPException(
                status_code=403,
                detail=(
                    "You do not have permission "
                    "to view this device"
                ),
            )

    return device


# ============================================================
# UPDATE DEVICE
# ADMIN + TECHNICIAN
# ============================================================

@router.put(
    "/{device_id}",
    response_model=DeviceResponse,
)
def update_device(
    device_id: int,
    device_update: DeviceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(
            "admin",
            "technician",
        )
    ),
):
    device = (
        db.query(Device)
        .filter(Device.id == device_id)
        .first()
    )

    if not device:
        raise HTTPException(
            status_code=404,
            detail="Device not found",
        )

    update_data = device_update.model_dump(
        exclude_unset=True
    )

    if (
        "serial_number" in update_data
        and update_data["serial_number"]
    ):
        existing_serial = (
            db.query(Device)
            .filter(
                Device.serial_number
                == update_data["serial_number"],
                Device.id != device_id,
            )
            .first()
        )

        if existing_serial:
            raise HTTPException(
                status_code=409,
                detail=(
                    "A device with this serial "
                    "number already exists"
                ),
            )

    for field, value in update_data.items():
        setattr(
            device,
            field,
            value,
        )

    try:
        log_action(
            db=db,
            user_id=current_user.id,
            action="update",
            resource_type="device",
            resource_id=device.id,
            details=(
                f"Updated device {device.id}"
            ),
        )

        db.commit()
        db.refresh(device)

    except IntegrityError:
        db.rollback()

        raise HTTPException(
            status_code=409,
            detail=(
                "Device could not be updated "
                "because a unique value already exists"
            ),
        )

    return device


# ============================================================
# DELETE DEVICE
# ADMIN ONLY
# ============================================================

@router.delete(
    "/{device_id}",
)
def delete_device(
    device_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles("admin")
    ),
):
    device = (
        db.query(Device)
        .filter(Device.id == device_id)
        .first()
    )

    if not device:
        raise HTTPException(
            status_code=404,
            detail="Device not found",
        )

    saved_device_id = device.id
    saved_device_name = device.device_name

    db.delete(device)

    log_action(
        db=db,
        user_id=current_user.id,
        action="delete",
        resource_type="device",
        resource_id=saved_device_id,
        details=(
            f"Deleted device "
            f"{saved_device_name}"
        ),
    )

    db.commit()

    return {
        "message": "Device deleted successfully",
        "device_id": saved_device_id,
    }

 # ============================================================
# ROTATE DEVICE API KEY
# ADMIN ONLY
# ============================================================

@router.post(
    "/{device_id}/rotate-api-key",
    response_model=DeviceRegistrationResponse,
)
def rotate_device_api_key(
    device_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles("admin")
    ),
):
    """
    Generate a new API key for an existing device.

    The previous API key becomes invalid immediately.
    The new raw API key is returned only once.
    """

    device = (
        db.query(Device)
        .filter(
            Device.id == device_id
        )
        .first()
    )

    if not device:
        raise HTTPException(
            status_code=404,
            detail="Device not found",
        )

    # Generate a new private key.
    raw_api_key = generate_device_api_key()

    # Store only the hash.
    device.api_key_hash = hash_device_api_key(
        raw_api_key
    )

    try:

        log_action(
            db=db,
            user_id=current_user.id,
            action="rotate_api_key",
            resource_type="device",
            resource_id=device.id,
            details=(
                f"API key rotated for device "
                f"{device.id} "
                f"({device.device_name})"
            ),
        )

        db.commit()
        db.refresh(device)

    except Exception as error:

        db.rollback()

        print(
            f"Device API key rotation error: {error}"
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "Unable to rotate device API key"
            ),
        )

    return DeviceRegistrationResponse(
        id=device.id,
        solar_system_id=device.solar_system_id,
        device_name=device.device_name,
        device_type=device.device_type,
        manufacturer=device.manufacturer,
        model=device.model,
        serial_number=device.serial_number,
        is_active=device.is_active,
        last_seen=device.last_seen,
        created_at=device.created_at,
        api_key=raw_api_key,
    )   