from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class MaintenanceCreate(BaseModel):
    solar_system_id: int
    issue: str
    action_taken: Optional[str] = None
    status: Optional[str] = "open"
    technician: Optional[str] = None


class MaintenanceUpdate(BaseModel):
    issue: Optional[str] = None
    action_taken: Optional[str] = None
    status: Optional[str] = None
    technician: Optional[str] = None


class MaintenanceResponse(MaintenanceCreate):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True