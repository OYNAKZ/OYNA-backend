from pydantic import BaseModel


class ZoneBase(BaseModel):
    branch_id: int
    name: str


class ZoneCreate(ZoneBase):
    pass


class ZoneRead(ZoneBase):
    id: int
