from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class AlertResponse(BaseModel):
    id: int
    solar_system_id: int
    telemetry_id: Optional[int] = None

    alert_type: str
    severity: str
    title: str
    message: str

    status: str
    needs_review: int

    created_at: datetime
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)