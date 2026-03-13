from pydantic import BaseModel


class ReservationBase(BaseModel):
    seat_id: int
    user_id: int
    status: str = "pending"


class ReservationCreate(ReservationBase):
    pass


class ReservationRead(ReservationBase):
    id: int
