from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.core.constants import SeatOperationalStatus
from app.schemas.branch import BranchSummary
from app.schemas.zone import ZoneSummary


class SeatBase(BaseModel):
    zone_id: int
    code: str
    seat_type: str
    is_active: bool = True
    is_maintenance: bool = False
    operational_status: str = SeatOperationalStatus.AVAILABLE.value
    x_position: float | None = None
    y_position: float | None = None


class SeatCreate(SeatBase):
    pass


class SeatUpdate(BaseModel):
    zone_id: int | None = None
    code: str | None = None
    seat_type: str | None = None
    is_active: bool | None = None
    is_maintenance: bool | None = None
    operational_status: str | None = None
    x_position: float | None = None
    y_position: float | None = None


class SeatRead(SeatBase):
    model_config = ConfigDict(from_attributes=True)

    id: int


class SeatSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    zone_id: int
    code: str
    seat_type: str
    is_active: bool
    is_maintenance: bool
    operational_status: str
    x_position: float | None
    y_position: float | None
    zone: ZoneSummary
    branch: BranchSummary


class SeatAvailabilitySlot(BaseModel):
    start: datetime
    end: datetime
    status: str


class SeatAvailabilityRead(BaseModel):
    seat_id: int
    date: str
    slots: list[SeatAvailabilitySlot]


class SeatStatusUpdate(BaseModel):
    operational_status: str
    reason: str | None = None


class SeatStatusHistoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    seat_id: int
    changed_by_user_id: int
    from_status: str
    to_status: str
    reason: str | None
    created_at: datetime
