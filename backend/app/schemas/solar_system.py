from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class SolarSystemCreate(BaseModel):
    customer_id: int
    inverter_brand: Optional[str] = None
    inverter_capacity_kva: Optional[float] = None
    battery_type: Optional[str] = None
    battery_capacity_kwh: Optional[float] = None
    panel_count: Optional[int] = None
    panel_wattage: Optional[float] = None
    location: Optional[str] = None


class SolarSystemUpdate(BaseModel):
    inverter_brand: Optional[str] = None
    inverter_capacity_kva: Optional[float] = None
    battery_type: Optional[str] = None
    battery_capacity_kwh: Optional[float] = None
    panel_count: Optional[int] = None
    panel_wattage: Optional[float] = None
    location: Optional[str] = None


class SolarSystemResponse(SolarSystemCreate):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True