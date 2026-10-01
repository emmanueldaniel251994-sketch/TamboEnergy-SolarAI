from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class DeviceCreate(BaseModel):
    solar_system_id: int = Field(gt=0)

    device_name: str = Field(
        min_length=2,
        max_length=150,
    )

    device_type: str = Field(
        default="monitoring_gateway",
        max_length=100,
    )

    manufacturer: Optional[str] = Field(
        default=None,
        max_length=150,
    )

    model: Optional[str] = Field(
        default=None,
        max_length=150,
    )

    serial_number: Optional[str] = Field(
        default=None,
        max_length=150,
    )


class DeviceUpdate(BaseModel):
    device_name: Optional[str] = Field(
        default=None,
        min_length=2,
        max_length=150,
    )

    device_type: Optional[str] = Field(
        default=None,
        max_length=100,
    )

    manufacturer: Optional[str] = Field(
        default=None,
        max_length=150,
    )

    model: Optional[str] = Field(
        default=None,
        max_length=150,
    )

    serial_number: Optional[str] = Field(
        default=None,
        max_length=150,
    )

    is_active: Optional[bool] = None


class DeviceResponse(BaseModel):
    id: int
    solar_system_id: int
    device_name: str
    device_type: str

    manufacturer: Optional[str] = None
    model: Optional[str] = None
    serial_number: Optional[str] = None

    is_active: bool
    last_seen: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(
        from_attributes=True
    )


class DeviceRegistrationResponse(DeviceResponse):
    api_key: str