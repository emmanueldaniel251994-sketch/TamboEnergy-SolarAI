import hashlib
import secrets


DEVICE_API_KEY_PREFIX = "tambo_dev_"


def generate_device_api_key() -> str:
    """
    Generate a cryptographically secure API key
    for a SolarAI monitoring device.
    """
    random_secret = secrets.token_urlsafe(32)

    return f"{DEVICE_API_KEY_PREFIX}{random_secret}"


def hash_device_api_key(api_key: str) -> str:
    """
    Create a SHA-256 digest of a device API key.

    The raw API key must never be stored
    in the database.
    """
    return hashlib.sha256(
        api_key.encode("utf-8")
    ).hexdigest()


def verify_device_api_key(
    api_key: str,
    stored_hash: str,
) -> bool:
    """
    Verify a supplied device API key
    against the stored digest.
    """
    supplied_hash = hash_device_api_key(api_key)

    return secrets.compare_digest(
        supplied_hash,
        stored_hash,
    )