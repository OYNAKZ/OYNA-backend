from __future__ import annotations

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.core.constants import ReservationStatus
from app.models.reservation import Reservation
from app.schemas.reservation import ReservationCreate


class ReservationRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, reservation_id: int) -> Reservation | None:
        return self.db.get(Reservation, reservation_id)

    def list_by_user(self, user_id: int) -> list[Reservation]:
        stmt = select(Reservation).where(Reservation.user_id == user_id).order_by(Reservation.id)
        return list(self.db.scalars(stmt))

    def list_all(self) -> list[Reservation]:
        return list(self.db.scalars(select(Reservation).order_by(Reservation.id)))

    def has_overlap(self, *, seat_id: int, start_at, end_at) -> bool:
        active_statuses = (
            ReservationStatus.PENDING.value,
            ReservationStatus.CONFIRMED.value,
            ReservationStatus.CHECKED_IN.value,
        )
        stmt = select(Reservation.id).where(
            and_(
                Reservation.seat_id == seat_id,
                Reservation.status.in_(active_statuses),
                Reservation.start_at < end_at,
                Reservation.end_at > start_at,
                or_(Reservation.cancelled_at.is_(None), Reservation.cancelled_at > start_at),
            )
        )
        return self.db.scalar(stmt) is not None

    def create(self, payload: ReservationCreate) -> Reservation:
        item = Reservation(**payload.model_dump())
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    def update(self, reservation: Reservation, **changes) -> Reservation:
        for field, value in changes.items():
            setattr(reservation, field, value)
        self.db.add(reservation)
        self.db.commit()
        self.db.refresh(reservation)
        return reservation


def list_items(db: Session) -> list[Reservation]:
    return ReservationRepository(db).list_all()


def create_item(db: Session, payload: ReservationCreate) -> Reservation:
    return ReservationRepository(db).create(payload)
