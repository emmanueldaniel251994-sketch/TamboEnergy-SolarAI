import os

from dotenv import load_dotenv


load_dotenv()


def _csv_env(name: str, default: str) -> list[str]:
    value = os.getenv(name, default)
    return [item.strip() for item in value.split(",") if item.strip()]


def _bool_env(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _int_env(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    return int(value.strip())


APP_ENV = os.getenv("APP_ENV", "development").strip().lower()
APP_VERSION = os.getenv("APP_VERSION", "1.0.0").strip()
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./tamboenergy_solarai.db",
).strip()

CORS_ORIGINS = _csv_env(
    "CORS_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173",
)

ALLOWED_HOSTS = _csv_env(
    "ALLOWED_HOSTS",
    "localhost,127.0.0.1,testserver",
)

SECRET_KEY = os.getenv("SECRET_KEY", "").strip()
ALGORITHM = os.getenv("ALGORITHM", "HS256").strip()
ACCESS_TOKEN_EXPIRE_MINUTES = _int_env(
    "ACCESS_TOKEN_EXPIRE_MINUTES",
    60,
)
JWT_ISSUER = os.getenv(
    "JWT_ISSUER",
    "tamboenergy-solarai",
).strip()
JWT_AUDIENCE = os.getenv(
    "JWT_AUDIENCE",
    "solarai-users",
).strip()

# Device request signing is optional for local development so existing
# test gateways remain easy to use, but it should be enabled in production.
DEVICE_REQUEST_SIGNING_REQUIRED = _bool_env(
    "DEVICE_REQUEST_SIGNING_REQUIRED",
    APP_ENV == "production",
)
DEVICE_REQUEST_MAX_SKEW_SECONDS = _int_env(
    "DEVICE_REQUEST_MAX_SKEW_SECONDS",
    300,
)
DEVICE_RATE_LIMIT_PER_MINUTE = _int_env(
    "DEVICE_RATE_LIMIT_PER_MINUTE",
    30,
)
DEVICE_NONCE_RETENTION_HOURS = _int_env(
    "DEVICE_NONCE_RETENTION_HOURS",
    24,
)


def validate_runtime_config() -> None:
    """Fail early on configuration that is unsafe for production."""

    if not SECRET_KEY:
        raise RuntimeError("SECRET_KEY is missing from environment configuration")

    if APP_ENV == "production":
        if len(SECRET_KEY) < 32:
            raise RuntimeError(
                "SECRET_KEY must contain at least 32 characters in production"
            )

        if "*" in CORS_ORIGINS:
            raise RuntimeError(
                "Wildcard CORS origins are not allowed in production"
            )

        if not DEVICE_REQUEST_SIGNING_REQUIRED:
            raise RuntimeError(
                "DEVICE_REQUEST_SIGNING_REQUIRED must be enabled in production"
            )
