from fastapi import HTTPException, status

from app.core.db import SessionLocal
from app.core.security import create_access_token, hash_password, verify_password
from app.repositories.user import UserRepository
from app.schemas.auth import TokenResponse
from app.schemas.user import UserCreate, UserRead


def authenticate_user(email: str, password: str) -> TokenResponse:
    with SessionLocal() as db:
        repo = UserRepository(db)
        user = repo.get_by_email(email)

        if user is None or not verify_password(password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is disabled",
            )

        token = create_access_token(subject=str(user.id))
        return TokenResponse(access_token=token)


def register_user(payload: UserCreate) -> UserRead:
    with SessionLocal() as db:
        repo = UserRepository(db)

        if repo.get_by_email(str(payload.email)):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered",
            )

        if repo.get_by_phone(payload.phone):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Phone already registered",
            )

        user = repo.create(payload, password_hash=hash_password(payload.password))
        return UserRead.model_validate(user)
