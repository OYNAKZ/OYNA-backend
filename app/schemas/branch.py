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


class BranchRead(BranchBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
