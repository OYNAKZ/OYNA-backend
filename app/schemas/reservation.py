from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.core.constants import ReservationStatus


class ReservationBase(BaseModel):
    seat_id: int
    user_id: int
    start_at: datetime
    end_at: datetime
    status: str = ReservationStatus.CONFIRMED.value
    expires_at: datetime | None = None
    cancelled_at: datetime | None = None


class ReservationCreate(ReservationBase):
    pass


class ReservationRead(ReservationBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
