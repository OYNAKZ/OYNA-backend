import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import delete, text

from app.core.constants import ScopeRole, UserRole
from app.core.db import SessionLocal, engine
from app.core.security import create_access_token, hash_password
from app.models import (
    Base,
    Branch,
    Club,
    Payment,
    PaymentWebhookEvent,
    Reservation,
    Seat,
    SeatStatusHistory,
    Session,
    StaffAssignment,
    User,
    Zone,
)


@pytest.fixture(scope="session", autouse=True)
def prepare_schema() -> None:
    engine.dispose()
    Base.metadata.drop_all(bind=engine)
    with engine.begin() as connection:
        connection.execute(text("DROP TABLE IF EXISTS alembic_version"))
    config = Config("alembic.ini")
    command.upgrade(config, "head")


@pytest.fixture(autouse=True)
def clean_db() -> None:
    with SessionLocal() as db:
        db.execute(delete(PaymentWebhookEvent))
        db.execute(delete(Payment))
        db.execute(delete(SeatStatusHistory))
        db.execute(delete(StaffAssignment))
        db.execute(delete(Session))
        db.execute(delete(Reservation))
        db.execute(delete(Seat))
        db.execute(delete(Zone))
        db.execute(delete(Branch))
        db.execute(delete(Club))
        db.execute(delete(User))
        db.commit()


def create_user_with_token(
    *,
    role: str = UserRole.USER.value,
    email: str,
    full_name: str = "Test User",
    club_id: int | None = None,
) -> tuple[User, dict[str, str]]:
    with SessionLocal() as db:
        user = User(
            full_name=full_name,
            club_id=club_id,
            email=email,
            phone=None,
            password_hash=hash_password("test-password-123"),
            role=role,
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        if role in (UserRole.OWNER.value, UserRole.CLUB_ADMIN.value) and club_id is not None:
            assignment = StaffAssignment(
                user_id=user.id,
                club_id=club_id,
                branch_id=None,
                role_in_scope=ScopeRole.OWNER.value if role == UserRole.OWNER.value else ScopeRole.CLUB_ADMIN.value,
                is_active=True,
            )
            db.add(assignment)
            db.commit()

        token = create_access_token(subject=str(user.id))
        headers = {"Authorization": f"Bearer {token}"}
        return user, headers
