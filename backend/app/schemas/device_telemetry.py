from typing import Optional

from pydantic import BaseModel, Field


class DeviceTelemetryCreate(BaseModel):
    """
    Telemetry payload accepted from an authenticated
    SolarAI monitoring device.

    solar_system_id is deliberately excluded.
    The backend determines the solar system from
    the authenticated device.
    """

    pv_voltage: Optional[float] = Field(
        default=None,
        ge=0,
    )

    pv_current: Optional[float] = None

    pv_power: Optional[float] = Field(
        default=None,
        ge=0,
    )

    battery_voltage: Optional[float] = Field(
        default=None,
        ge=0,
    )

    battery_current: Optional[float] = None

    battery_soc: Optional[float] = Field(
        default=None,
        ge=0,
        le=100,
    )

    load_power: Optional[float] = Field(
        default=None,
        ge=0,
    )

    temperature: Optional[float] = None

    error_code: Optional[str] = None