from pydantic import BaseModel


class SeatBase(BaseModel):
    zone_id: int
    code: str


class SeatCreate(SeatBase):
    pass


class SeatRead(SeatBase):
    id: int
