from fastapi import APIRouter, Depends

from app.api.dependencies import get_current_user
from app.models.user import User
from app.schemas.user import UserRead
from app.services.user import get_all_users, get_user_by_id

router = APIRouter()


@router.get("", response_model=list[UserRead])
def get_users() -> list[UserRead]:
    return get_all_users()


@router.get("/me", response_model=UserRead)
def get_me(current_user: User = Depends(get_current_user)) -> UserRead:
    return UserRead.model_validate(current_user)


@router.get("/{user_id}", response_model=UserRead)
def get_user(user_id: int) -> UserRead:
    return get_user_by_id(user_id)
