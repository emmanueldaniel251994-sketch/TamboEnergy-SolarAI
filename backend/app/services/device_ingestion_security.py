from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import (
    DEVICE_NONCE_RETENTION_HOURS,
    DEVICE_RATE_LIMIT_PER_MINUTE,
    DEVICE_REQUEST_MAX_SKEW_SECONDS,
    DEVICE_REQUEST_SIGNING_REQUIRED,
)
from app.device_security import verify_device_request_signature
from app.models.device_request_nonce import DeviceRequestNonce
from app.models.telemetry import Telemetry


def _parse_request_timestamp(value: str | None) -> datetime | None:
    if value is None:
        return None

    try:
        timestamp = int(value)
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=401,
            detail="Invalid device request timestamp",
        )

    try:
        return datetime.fromtimestamp(timestamp, tz=timezone.utc)
    except (OverflowError, OSError, ValueError):
        raise HTTPException(
            status_code=401,
            detail="Invalid device request timestamp",
        )


def verify_device_request(
    *,
    api_key: str,
    request_timestamp: str | None,
    nonce: str | None,
    signature: str | None,
    payload: dict,
) -> datetime | None:
    """Validate freshness and HMAC signature for a device request."""

    signing_fields = [request_timestamp, nonce, signature]
    signing_supplied = any(value is not None for value in signing_fields)

    if DEVICE_REQUEST_SIGNING_REQUIRED and not all(signing_fields):
        raise HTTPException(
            status_code=401,
            detail="Signed device request headers are required",
        )

    if not signing_supplied:
        return None

    if not all(signing_fields):
        raise HTTPException(
            status_code=401,
            detail="Incomplete signed device request headers",
        )

    if not nonce or len(nonce) > 128:
        raise HTTPException(status_code=401, detail="Invalid device nonce")

    parsed_timestamp = _parse_request_timestamp(request_timestamp)
    assert parsed_timestamp is not None

    now = datetime.now(timezone.utc)
    skew = abs((now - parsed_timestamp).total_seconds())
    if skew > DEVICE_REQUEST_MAX_SKEW_SECONDS:
        raise HTTPException(
            status_code=401,
            detail="Device request timestamp is outside the allowed time window",
        )

    if not verify_device_request_signature(
        api_key=api_key,
        timestamp=request_timestamp,
        nonce=nonce,
        payload=payload,
        supplied_signature=signature,
    ):
        raise HTTPException(status_code=401, detail="Invalid device request signature")

    return parsed_timestamp


def reserve_device_nonce(
    *,
    db: Session,
    device_id: int,
    nonce: str | None,
    request_timestamp: datetime | None,
) -> None:
    """Persist a signed-request nonce so the exact request cannot be replayed."""

    if nonce is None or request_timestamp is None:
        return

    retention_cutoff = datetime.now(timezone.utc) - timedelta(
        hours=DEVICE_NONCE_RETENTION_HOURS
    )
    (
        db.query(DeviceRequestNonce)
        .filter(
            DeviceRequestNonce.device_id == device_id,
            DeviceRequestNonce.created_at < retention_cutoff,
        )
        .delete(synchronize_session=False)
    )

    existing = (
        db.query(DeviceRequestNonce)
        .filter(
            DeviceRequestNonce.device_id == device_id,
            DeviceRequestNonce.nonce == nonce,
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=409,
            detail="Device request replay detected",
        )

    db.add(
        DeviceRequestNonce(
            device_id=device_id,
            nonce=nonce,
            request_timestamp=request_timestamp,
        )
    )

    try:
        db.flush()
    except IntegrityError:
        raise HTTPException(
            status_code=409,
            detail="Device request replay detected",
        )


def enforce_device_rate_limit(*, db: Session, device_id: int) -> None:
    """Database-backed per-device fixed-window rate limit for the MVP."""

    if DEVICE_RATE_LIMIT_PER_MINUTE <= 0:
        return

    cutoff = datetime.now(timezone.utc) - timedelta(minutes=1)
    recent_count = (
        db.query(Telemetry)
        .filter(
            Telemetry.device_id == device_id,
            Telemetry.created_at >= cutoff,
        )
        .count()
    )

    if recent_count >= DEVICE_RATE_LIMIT_PER_MINUTE:
        raise HTTPException(
            status_code=429,
            detail="Device telemetry rate limit exceeded",
            headers={"Retry-After": "60"},
        )
