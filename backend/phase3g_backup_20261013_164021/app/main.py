from app.routes.manufacturer_import import router as manufacturer_import_router
from app.routes.manufacturer_chat import router as manufacturer_chat_router
from app.routes.manufacturer_diagnostics import router as manufacturer_diagnostics_router
from app.routes.universal_diagnostics import router as universal_diagnostics_router
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session
from starlette.middleware.trustedhost import TrustedHostMiddleware
from app.routes.diagnostic_conversation import router as ai_conversation_router

from app.config import (
    ALLOWED_HOSTS,
    APP_ENV,
    APP_VERSION,
    CORS_ORIGINS,
    validate_runtime_config,
)
from app.database import get_db
from app.routes.auth import router as auth_router
from app.routes.customer import router as customers_router
from app.routes.solar_system import router as solar_systems_router
from app.routes.maintenance import router as maintenance_router
from app.routes.audit import router as audit_router
from app.routes.telemetry import router as telemetry_router
from app.routes.device_telemetry import router as device_telemetry_router
from app.routes.device import router as device_router
from app.routes import diagnostics, alerts, dashboard
from app.routes.ai_assistant import router as ai_assistant_router
from app.routes.diagnostic_quality import router as diagnostic_quality_router
from app.routes.ai_sessions import router as ai_sessions_router
from app.routes.manufacturers import router as manufacturers_router
from app.routes.equipment_models import router as equipment_models_router
from app.routes.technical_documents import router as technical_documents_router
from app.routes.equipment_fault_codes import router as equipment_fault_codes_router
from app.routes.manufacturer_verification import router as manufacturer_verification_router

validate_runtime_config()

app = FastAPI(
    title="TamboEnergy SolarAI API",
    description=(
        "AI-powered solar monitoring, diagnostics, maintenance and "
        "energy management platform by TamboEnergy System"
    ),
    version=APP_VERSION,
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=ALLOWED_HOSTS,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=[
        "Authorization",
        "Content-Type",
        "Accept",
        "X-Device-API-Key",
        "X-Device-Timestamp",
        "X-Device-Nonce",
        "X-Device-Signature",
    ],
)


@app.middleware("http")
async def security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    if APP_ENV == "production":
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )
    return response


app.include_router(manufacturer_import_router)
app.include_router(manufacturer_chat_router)
app.include_router(manufacturer_diagnostics_router)
app.include_router(auth_router)
app.include_router(customers_router)
app.include_router(solar_systems_router)
app.include_router(maintenance_router)
app.include_router(audit_router)
app.include_router(telemetry_router)
app.include_router(device_router)
app.include_router(device_telemetry_router)
app.include_router(diagnostics.router)
app.include_router(alerts.router)
app.include_router(dashboard.router)
app.include_router(ai_assistant_router)
app.include_router(ai_conversation_router)
app.include_router(diagnostic_quality_router)
app.include_router(ai_sessions_router)
app.include_router(manufacturers_router)
app.include_router(equipment_models_router)
app.include_router(technical_documents_router)
app.include_router(equipment_fault_codes_router)
app.include_router(manufacturer_verification_router)

@app.get("/")
def root():
    return {
        "company": "TamboEnergy System",
        "product": "SolarAI",
        "version": APP_VERSION,
        "message": "TamboEnergy SolarAI API is running",
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "TamboEnergy SolarAI",
        "version": APP_VERSION,
    }


@app.get("/health/ready")
def readiness_check(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {
        "status": "ready",
        "database": "reachable",
        "version": APP_VERSION,
    }

app.include_router(universal_diagnostics_router)






