from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.core.constants import ReservationStatus
from app.schemas.seat import SeatSummary


class ReservationBase(BaseModel):
    seat_id: int
    start_at: datetime
    end_at: datetime
    status: ReservationStatus = ReservationStatus.CONFIRMED
    idempotency_key: str | None = None
    expires_at: datetime | None = None
    cancelled_at: datetime | None = None


class ReservationCreate(BaseModel):
    seat_id: int
    start_at: datetime
    end_at: datetime
    user_id: int | None = None
    status: ReservationStatus = ReservationStatus.CONFIRMED
    idempotency_key: str | None = None
    expires_at: datetime | None = None
    cancelled_at: datetime | None = None


class ReservationHoldCreate(BaseModel):
    seat_id: int
    start_at: datetime
    end_at: datetime
    user_id: int | None = None
    idempotency_key: str
    hold_ttl_seconds: int | None = None


class ReservationRead(ReservationBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int


class ReservationDetailRead(ReservationRead):
    seat: SeatSummary
