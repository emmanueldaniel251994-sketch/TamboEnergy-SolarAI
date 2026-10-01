from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import CORS_ORIGINS

# ============================================================
# ROUTERS
# ============================================================

from app.routes.auth import (
    router as auth_router
)

from app.routes.customer import (
    router as customers_router
)

from app.routes.solar_system import (
    router as solar_systems_router
)

from app.routes.maintenance import (
    router as maintenance_router
)

from app.routes.audit import (
    router as audit_router
)

from app.routes.telemetry import (
    router as telemetry_router
)

from app.routes.device_telemetry import (
    router as device_telemetry_router,
)

from app.routes import diagnostics

from app.routes import alerts

from app.routes import dashboard

from app.routes.device import router as device_router

# ============================================================
# CREATE FASTAPI APPLICATION
# ============================================================

app = FastAPI(
    title="TamboEnergy SolarAI API",

    description=(
        "AI-powered solar monitoring, diagnostics, "
        "maintenance and energy management platform "
        "by TamboEnergy System"
    ),

    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# REGISTER ROUTERS
# ============================================================

app.include_router(
    auth_router
)

app.include_router(
    customers_router
)

app.include_router(
    solar_systems_router
)

app.include_router(
    maintenance_router
)

app.include_router(
    audit_router
)

app.include_router(
    telemetry_router
)

app.include_router(
    device_router
)

app.include_router(
    device_telemetry_router
)


app.include_router(
    diagnostics.router
)

app.include_router(
    alerts.router
)

app.include_router(
    dashboard.router
    )


# ============================================================
# ROOT ENDPOINT
# ============================================================

@app.get("/")
def root():

    return {
        "company": "TamboEnergy System",
        "product": "SolarAI",
        "version": "2.0.0",
        "message": "TamboEnergy SolarAI API is running"
    }


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/health")
def health_check():

    return {
        "status": "healthy",
        "service": "TamboEnergy SolarAI",
        "version": "2.0.0"
    }