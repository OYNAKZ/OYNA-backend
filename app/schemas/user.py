from pydantic import BaseModel, ConfigDict, EmailStr

from app.core.constants import UserRole


class UserCreate(BaseModel):
    full_name: str | None = None
    club_id: int | None = None
    email: EmailStr
    phone: str | None = None
    password: str
    role: str = UserRole.USER.value


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str | None
    club_id: int | None
    email: EmailStr
    phone: str | None
    role: str
    is_active: bool
