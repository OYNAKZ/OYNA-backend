from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.branch import Branch
from app.models.seat import Seat
from app.models.zone import Zone
from app.schemas.seat import SeatCreate, SeatUpdate


class SeatRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, seat_id: int) -> Seat | None:
        return self.db.get(Seat, seat_id)

    def list_by_branch(self, branch_id: int) -> list[Seat]:
        stmt = (
            select(Seat)
            .join(Zone, Seat.zone_id == Zone.id)
            .join(Branch, Zone.branch_id == Branch.id)
            .where(Branch.id == branch_id)
            .order_by(Seat.id)
        )
        return list(self.db.scalars(stmt))

    def create(self, payload: SeatCreate) -> Seat:
        item = Seat(**payload.model_dump())
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    def update(self, seat: Seat, payload: SeatUpdate) -> Seat:
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(seat, field, value)
        self.db.add(seat)
        self.db.commit()
        self.db.refresh(seat)
        return seat


def list_items(db: Session) -> list[Seat]:
    return list(db.scalars(select(Seat).order_by(Seat.id)))


def create_item(db: Session, payload: SeatCreate) -> Seat:
    return SeatRepository(db).create(payload)
