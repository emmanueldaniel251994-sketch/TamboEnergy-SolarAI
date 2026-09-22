from datetime import datetime
from typing import Optional

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)


class TelemetryCreate(BaseModel):
    solar_system_id: int = Field(
        gt=0
    )

    pv_voltage: Optional[float] = Field(
        default=None,
        ge=0,
        le=1000,
    )

    pv_current: Optional[float] = Field(
        default=None,
        ge=0,
        le=500,
    )

    pv_power: Optional[float] = Field(
        default=None,
        ge=0,
        le=500000,
    )

    battery_voltage: Optional[float] = Field(
        default=None,
        ge=0,
        le=1000,
    )

    # Battery current may be negative when the
    # battery is discharging.
    battery_current: Optional[float] = Field(
        default=None,
        ge=-1000,
        le=1000,
    )

    battery_soc: Optional[float] = Field(
        default=None,
        ge=0,
        le=100,
    )

    load_power: Optional[float] = Field(
        default=None,
        ge=0,
        le=500000,
    )

    temperature: Optional[float] = Field(
        default=None,
        ge=-50,
        le=150,
    )

    error_code: Optional[str] = Field(
        default=None,
        max_length=100,
    )

    status: str = Field(
        default="normal",
        max_length=50,
    )


class TelemetryResponse(TelemetryCreate):
    id: int

    fault_type: Optional[str] = None
    fault_severity: Optional[str] = None

    ml_prediction: Optional[str] = None
    ml_confidence: Optional[float] = None
    ml_prediction_available: int = 1

    data_quality_score: float = 100.0
    missing_fields: Optional[str] = None

    prediction_agreement: Optional[str] = None
    final_diagnosis: Optional[str] = None

    needs_review: int = 0

    created_at: datetime

    model_config = ConfigDict(
        from_attributes=True
    )