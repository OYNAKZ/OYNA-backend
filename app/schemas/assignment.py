from datetime import datetime

from pydantic import BaseModel, ConfigDict


class StaffAssignmentCreate(BaseModel):
    user_id: int
    club_id: int
    branch_id: int | None = None
    role_in_scope: str


class StaffAssignmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    club_id: int
    branch_id: int | None
    role_in_scope: str
    is_active: bool
    created_at: datetime


class StaffAssignmentScopeRead(BaseModel):
    user_id: int
    assignments: list[StaffAssignmentRead]
