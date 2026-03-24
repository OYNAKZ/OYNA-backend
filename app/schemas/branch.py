from datetime import time

from pydantic import BaseModel, ConfigDict


class BranchBase(BaseModel):
    club_id: int
    name: str
    address: str
    city: str
    latitude: float
    longitude: float
    open_time: time
    close_time: time
    is_active: bool = True


class BranchCreate(BranchBase):
    pass


class BranchUpdate(BaseModel):
    club_id: int | None = None
    name: str | None = None
    address: str | None = None
    city: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    open_time: time | None = None
    close_time: time | None = None
    is_active: bool | None = None


class BranchRead(BranchBase):
    model_config = ConfigDict(from_attributes=True)

    id: int


class BranchSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    club_id: int
    name: str
    address: str
    city: str
    open_time: time
    close_time: time
    is_active: bool
