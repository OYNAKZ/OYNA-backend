from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError

from app.core.config import settings
from app.core.constants import UserRole
from app.core.db import SessionLocal
from app.core.security import create_access_token, hash_password, verify_password
from app.repositories.user import UserRepository
from app.schemas.auth import RegisterResponse, TokenResponse, UserPublic
from app.schemas.user import UserCreate, UserRead
from app.services import events


class UserAlreadyExistsError(Exception):
    pass


class PasswordPolicyError(Exception):
    pass


def normalize_email(email: str) -> str:
    return email.strip().casefold()


def validate_password_policy(password: str) -> None:
    if len(password) < settings.auth_password_min_len:
        raise PasswordPolicyError(f"Password must be at least {settings.auth_password_min_len} characters long")
    if len(password) > settings.auth_password_max_len:
        raise PasswordPolicyError(f"Password must be at most {settings.auth_password_max_len} characters long")


def authenticate_user(email: str, password: str) -> TokenResponse:
    with SessionLocal() as db:
        repo = UserRepository(db)
        user = repo.get_by_email(normalize_email(email))

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

        email = normalize_email(str(payload.email))
        validate_password_policy(payload.password)

        if repo.get_by_email(email):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered",
            )

        if payload.phone and repo.get_by_phone(payload.phone):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Phone already registered",
            )

        payload.email = email
        user = repo.create(payload, password_hash=hash_password(payload.password))
        return UserRead.model_validate(user)


def register_user_account(*, email: str, password: str, full_name: str | None = None) -> RegisterResponse:
    email_normalized = normalize_email(email)
    validate_password_policy(password)
    password_hash = hash_password(password)

    with SessionLocal() as db:
        repo = UserRepository(db)
        try:
            user = repo.create_user(
                email=email_normalized,
                password_hash=password_hash,
                full_name=full_name,
                role=UserRole.USER.value,
            )
            db.commit()
            db.refresh(user)
        except IntegrityError as exc:
            if settings.auth_anti_enumeration:
                return RegisterResponse(
                    user=UserPublic(
                        id=0,
                        email=email_normalized,
                        full_name=full_name,
                        is_email_verified=False,
                        is_active=True,
                        created_at=datetime.now(timezone.utc),
                    ),
                    verification_required=settings.auth_require_email_verification,
                )
            raise UserAlreadyExistsError() from exc

    verification_required = settings.auth_require_email_verification
    events.publish_user_registered(
        user_id=user.id,
        email=user.email,
        verification_required=verification_required,
    )
    return RegisterResponse(
        user=UserPublic.model_validate(user),
        verification_required=verification_required,
    )
