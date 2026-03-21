from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.core.constants import SessionStatus


class SessionBase(BaseModel):
    reservation_id: int
    seat_id: int
    user_id: int
    started_at: datetime
    planned_end_at: datetime
    ended_at: datetime | None = None
    status: str = SessionStatus.ACTIVE.value


class SessionCreate(BaseModel):
    reservation_id: int
    seat_id: int | None = None
    user_id: int | None = None
    started_at: datetime
    planned_end_at: datetime
    ended_at: datetime | None = None
    status: str = SessionStatus.ACTIVE.value


class SessionRead(SessionBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
