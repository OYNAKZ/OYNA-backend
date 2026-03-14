from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.reservation import Reservation
from app.schemas.reservation import ReservationCreate, ReservationRead


def list_items(db: Session) -> list[Reservation]:
    return list(db.scalars(select(Reservation).order_by(Reservation.id)))


def create_item(db: Session, payload: ReservationCreate) -> Reservation:
    item = Reservation(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item
