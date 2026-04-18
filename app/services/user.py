from fastapi import HTTPException, status

from app.core.db import SessionLocal
from app.core.constants import UserRole
from app.models.user import User
from app.repositories.user import UserRepository
from app.schemas.user import UserRead
from app.services.policies import ensure_self_or_platform_admin


def get_all_users(current_user: User) -> list[UserRead]:
    if current_user.role != UserRole.PLATFORM_ADMIN.value:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient scope")
    with SessionLocal() as db:
        users = UserRepository(db).get_all()
        return [UserRead.model_validate(u) for u in users]


def get_user_by_id(user_id: int, current_user: User) -> UserRead:
    ensure_self_or_platform_admin(current_user, user_id)
    with SessionLocal() as db:
        user = UserRepository(db).get_by_id(user_id)
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        return UserRead.model_validate(user)
