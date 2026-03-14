from pydantic import BaseModel, ConfigDict


class ZoneBase(BaseModel):
    branch_id: int
    name: str
    zone_type: str
    description: str | None = None
    is_active: bool = True


class ZoneCreate(ZoneBase):
    pass


class ZoneRead(ZoneBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
