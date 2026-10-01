import os

from dotenv import load_dotenv


load_dotenv()


def _csv_env(name: str, default: str) -> list[str]:
    value = os.getenv(name, default)
    return [item.strip() for item in value.split(",") if item.strip()]


APP_ENV = os.getenv("APP_ENV", "development").strip().lower()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./tamboenergy_solarai.db",
).strip()

CORS_ORIGINS = _csv_env(
    "CORS_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173",
)
