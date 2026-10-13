from typing import Literal
from pydantic import BaseModel, Field


class EquipmentProfile(BaseModel):
    equipment_model_id: int | None = Field(default=None, gt=0)
    system_type: Literal['residential', 'commercial', 'industrial', 'utility', 'unknown'] = 'unknown'
    rated_capacity_kva: float | None = Field(default=None, gt=0)
    phase_configuration: Literal['single_phase', 'three_phase', 'unknown'] = 'unknown'
    ac_voltage_v: float | None = Field(default=None, gt=0)
    dc_voltage_v: float | None = Field(default=None, gt=0)
    inverter_brand: str | None = Field(default=None, max_length=120)
    inverter_model: str | None = Field(default=None, max_length=120)
    inverter_type: str | None = Field(default=None, max_length=100)
    battery_brand: str | None = Field(default=None, max_length=120)
    battery_model: str | None = Field(default=None, max_length=120)
    battery_technology: str | None = Field(default=None, max_length=100)
    battery_voltage_v: float | None = Field(default=None, gt=0)
    battery_capacity_kwh: float | None = Field(default=None, gt=0)
    pv_capacity_kwp: float | None = Field(default=None, gt=0)
    panel_brand: str | None = Field(default=None, max_length=120)
    panel_model: str | None = Field(default=None, max_length=120)
    panel_count: int | None = Field(default=None, gt=0)
    charge_controller_brand: str | None = Field(default=None, max_length=120)
    charge_controller_model: str | None = Field(default=None, max_length=120)
    monitoring_protocol: str | None = Field(default=None, max_length=120)
    transformer_present: bool | None = None
    transformer_capacity_kva: float | None = Field(default=None, gt=0)
    bess_present: bool | None = None
    scada_present: bool | None = None
    pv_voltage_v: float | None = Field(default=None, ge=0)
    pv_power_w: float | None = Field(default=None, ge=0)
    battery_soc_percent: float | None = Field(default=None, ge=0, le=100)
    fault_code: str | None = Field(default=None, max_length=100)
    fault_category: Literal['fault', 'warning', 'unknown'] = 'unknown'
    symptoms: str | None = Field(default=None, max_length=2000)
    grid_or_generator: Literal['grid', 'generator', 'both', 'none', 'unknown'] = 'unknown'

    @property
    def industrial_risk(self) -> bool:
        # Power rating is not voltage class; unknown voltage is not assumed safe.
        return self.system_type in ('industrial', 'utility') or (self.rated_capacity_kva or 0) >= 100 or (self.ac_voltage_v or 0) > 1000 or (self.dc_voltage_v or 0) > 1500
