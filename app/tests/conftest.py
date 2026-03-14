import pytest
from sqlalchemy import delete

from app.core.db import SessionLocal
from app.models import Branch, Club, Reservation, Seat, Session, User, Zone


@pytest.fixture(autouse=True)
def clean_db() -> None:
    with SessionLocal() as db:
        db.execute(delete(Session))
        db.execute(delete(Reservation))
        db.execute(delete(Seat))
        db.execute(delete(Zone))
        db.execute(delete(Branch))
        db.execute(delete(Club))
        db.execute(delete(User))
        db.commit()
