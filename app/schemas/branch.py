from pydantic import BaseModel


class BranchBase(BaseModel):
    club_id: int
    name: str


class BranchCreate(BranchBase):
    pass


class BranchRead(BranchBase):
    id: int
