import hashlib
import hmac
import json
import secrets
from typing import Any

DEVICE_API_KEY_PREFIX = "tambo_dev_"
DEVICE_SIGNATURE_VERSION = "v1"


def generate_device_api_key() -> str:
    random_secret = secrets.token_urlsafe(32)
    return f"{DEVICE_API_KEY_PREFIX}{random_secret}"


def hash_device_api_key(api_key: str) -> str:
    return hashlib.sha256(api_key.encode("utf-8")).hexdigest()


def verify_device_api_key(api_key: str, stored_hash: str) -> bool:
    supplied_hash = hash_device_api_key(api_key)
    return secrets.compare_digest(supplied_hash, stored_hash)


def canonical_device_payload(payload: dict[str, Any]) -> str:
    """Create stable JSON used by both gateways and the API for signing."""
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def create_device_request_signature(
    api_key: str,
    timestamp: str,
    nonce: str,
    payload: dict[str, Any],
) -> str:
    payload_hash = hashlib.sha256(
        canonical_device_payload(payload).encode("utf-8")
    ).hexdigest()
    message = f"{DEVICE_SIGNATURE_VERSION}.{timestamp}.{nonce}.{payload_hash}"
    return hmac.new(
        api_key.encode("utf-8"),
        message.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def verify_device_request_signature(
    api_key: str,
    timestamp: str,
    nonce: str,
    payload: dict[str, Any],
    supplied_signature: str,
) -> bool:
    expected = create_device_request_signature(
        api_key=api_key,
        timestamp=timestamp,
        nonce=nonce,
        payload=payload,
    )
    return secrets.compare_digest(expected, supplied_signature)
