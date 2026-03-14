from sqlalchemy.orm import Session

from app.repositories import reservation as repository
from app.schemas.reservation import ReservationCreate, ReservationRead


def list_reservations(db: Session) -> list[ReservationRead]:
    return repository.list_items(db)


def create_reservation(db: Session, payload: ReservationCreate) -> ReservationRead:
    return repository.create_item(db, payload)
