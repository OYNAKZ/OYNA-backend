from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.db import SessionLocal
from app.models.user import User
from app.schemas.auth import LoginRequest
from app.schemas.user import UserCreate


class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_all(self) -> list[User]:
        return list(self.db.scalars(select(User)))

    def get_by_id(self, user_id: int) -> User | None:
        return self.db.get(User, user_id)

    def get_by_email(self, email: str) -> User | None:
        stmt = select(User).where(User.email == email)
        return self.db.scalar(stmt)

    def get_by_phone(self, phone: str) -> User | None:
        stmt = select(User).where(User.phone == phone)
        return self.db.scalar(stmt)

    def create(self, payload: UserCreate, password_hash: str) -> User:
        item = User(
            full_name=payload.full_name,
            email=str(payload.email),
            phone=payload.phone,
            password_hash=password_hash,
            role=payload.role,
        )
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    def create_user(
        self,
        *,
        email: str,
        password_hash: str,
        full_name: str | None = None,
        phone: str | None = None,
        role: str,
    ) -> User:
        user = User(
            email=email,
            password_hash=password_hash,
            full_name=full_name,
            phone=phone,
            role=role,
        )
        self.db.add(user)
        try:
            self.db.flush()
        except IntegrityError:
            self.db.rollback()
            raise
        return user


def get_by_email(*args) -> dict[str, str] | None:
    if len(args) == 1:
        payload = args[0]
        with SessionLocal() as db:
            return _get_by_login_payload(db, payload)

    db, payload = args
    return _get_by_login_payload(db, payload)


def _get_by_login_payload(db: Session, payload: LoginRequest) -> dict[str, str] | None:
    stmt = select(User).where(or_(User.email == payload.email, User.phone == payload.email))
    user = db.scalar(stmt)
    if user is None:
        return None
    return {"id": str(user.id), "email": user.email, "password": user.password_hash}
