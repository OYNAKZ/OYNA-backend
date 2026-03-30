from fastapi import HTTPException, status

from app.core.db import SessionLocal
from app.repositories.user import UserRepository
from app.schemas.user import UserRead


def get_all_users() -> list[UserRead]:
    with SessionLocal() as db:
        users = UserRepository(db).get_all()
        return [UserRead.model_validate(u) for u in users]


def get_user_by_id(user_id: int) -> UserRead:
    with SessionLocal() as db:
        user = UserRepository(db).get_by_id(user_id)
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        return UserRead.model_validate(user)
