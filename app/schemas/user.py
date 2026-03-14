from pydantic import BaseModel, ConfigDict, EmailStr

from app.core.constants import UserRole


class UserCreate(BaseModel):
    full_name: str
    email: EmailStr
    phone: str
    password: str
    role: str = UserRole.USER.value


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    email: EmailStr
    phone: str
    role: str
    is_active: bool
