from pydantic import BaseModel, ConfigDict


class ClubBase(BaseModel):
    name: str
    description: str | None = None
    is_active: bool = True


class ClubCreate(ClubBase):
    pass


class ClubRead(ClubBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
