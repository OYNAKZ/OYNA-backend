from pydantic import BaseModel, ConfigDict


class SeatBase(BaseModel):
    zone_id: int
    code: str
    seat_type: str
    is_active: bool = True
    is_maintenance: bool = False
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
    x_position: float | None = None
    y_position: float | None = None


class SeatRead(SeatBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
