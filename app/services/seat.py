from sqlalchemy.orm import Session

from app.repositories import seat as repository
from app.schemas.seat import SeatCreate, SeatRead


def list_seats(db: Session) -> list[SeatRead]:
    return repository.list_items(db)


def create_seat(db: Session, payload: SeatCreate) -> SeatRead:
    return repository.create_item(db, payload)
