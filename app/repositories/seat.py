from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.seat import Seat
from app.schemas.seat import SeatCreate, SeatRead


def list_items(db: Session) -> list[Seat]:
    return list(db.scalars(select(Seat).order_by(Seat.id)))


def create_item(db: Session, payload: SeatCreate) -> Seat:
    item = Seat(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item
