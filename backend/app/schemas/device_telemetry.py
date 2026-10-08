from typing import Optional

from pydantic import BaseModel, Field


class DeviceTelemetryCreate(BaseModel):
    """Telemetry accepted from an authenticated SolarAI gateway."""

    # A gateway-generated identifier makes telemetry retries idempotent.
    event_id: Optional[str] = Field(
        default=None,
        min_length=8,
        max_length=100,
        pattern=r"^[A-Za-z0-9._:-]+$",
    )

    pv_voltage: Optional[float] = Field(default=None, ge=0, le=1000)
    pv_current: Optional[float] = Field(default=None, ge=0, le=500)
    pv_power: Optional[float] = Field(default=None, ge=0, le=500000)
    battery_voltage: Optional[float] = Field(default=None, ge=0, le=1000)
    battery_current: Optional[float] = Field(default=None, ge=-1000, le=1000)
    battery_soc: Optional[float] = Field(default=None, ge=0, le=100)
    load_power: Optional[float] = Field(default=None, ge=0, le=500000)
    temperature: Optional[float] = Field(default=None, ge=-50, le=150)
    error_code: Optional[str] = Field(default=None, max_length=100)
