from dataclasses import dataclass

from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.device_security import hash_device_api_key
from app.models.device import Device


@dataclass(frozen=True)
class AuthenticatedDevice:
    device: Device
    api_key: str
    request_timestamp: str | None
    nonce: str | None
    signature: str | None


def get_current_device(
    x_device_api_key: str = Header(..., alias="X-Device-API-Key"),
    x_device_timestamp: str | None = Header(
        default=None,
        alias="X-Device-Timestamp",
    ),
    x_device_nonce: str | None = Header(
        default=None,
        alias="X-Device-Nonce",
    ),
    x_device_signature: str | None = Header(
        default=None,
        alias="X-Device-Signature",
    ),
    db: Session = Depends(get_db),
) -> AuthenticatedDevice:
    if not x_device_api_key.startswith("tambo_dev_"):
        raise HTTPException(status_code=401, detail="Invalid device API key")

    api_key_hash = hash_device_api_key(x_device_api_key)
    device = db.query(Device).filter(Device.api_key_hash == api_key_hash).first()

    if not device:
        raise HTTPException(status_code=401, detail="Invalid device API key")

    if not device.is_active:
        raise HTTPException(status_code=403, detail="Device is inactive")

    return AuthenticatedDevice(
        device=device,
        api_key=x_device_api_key,
        request_timestamp=x_device_timestamp,
        nonce=x_device_nonce,
        signature=x_device_signature,
    )
