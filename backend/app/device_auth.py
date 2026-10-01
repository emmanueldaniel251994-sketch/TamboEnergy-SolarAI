from fastapi import (
    Depends,
    Header,
    HTTPException,
)

from sqlalchemy.orm import Session

from app.database import get_db
from app.models.device import Device

from app.device_security import (
    hash_device_api_key,
)


def get_current_device(
    x_device_api_key: str = Header(
        ...,
        alias="X-Device-API-Key",
    ),
    db: Session = Depends(get_db),
) -> Device:
    """
    Authenticate a SolarAI monitoring device
    using its private API key.
    """

    # --------------------------------------------------------
    # BASIC KEY VALIDATION
    # --------------------------------------------------------

    if not x_device_api_key.startswith(
        "tambo_dev_"
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid device API key",
        )

    # --------------------------------------------------------
    # HASH RECEIVED KEY
    # --------------------------------------------------------

    api_key_hash = hash_device_api_key(
        x_device_api_key
    )

    # --------------------------------------------------------
    # FIND DEVICE
    # --------------------------------------------------------

    device = (
        db.query(Device)
        .filter(
            Device.api_key_hash
            == api_key_hash
        )
        .first()
    )

    if not device:
        raise HTTPException(
            status_code=401,
            detail="Invalid device API key",
        )

    # --------------------------------------------------------
    # CHECK DEVICE STATUS
    # --------------------------------------------------------

    if not device.is_active:
        raise HTTPException(
            status_code=403,
            detail="Device is inactive",
        )

    return device