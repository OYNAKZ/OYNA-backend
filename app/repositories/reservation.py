from __future__ import annotations

from datetime import date, datetime, time, timezone

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session, joinedload

from app.core.constants import ACTIVE_RESERVATION_STATUSES
from app.models.branch import Branch
from app.models.reservation import Reservation
from app.models.seat import Seat
from app.models.zone import Zone
from app.schemas.reservation import ReservationCreate


class ReservationRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, reservation_id: int) -> Reservation | None:
        return self.db.get(Reservation, reservation_id)

    def get_by_id_with_location(self, reservation_id: int) -> Reservation | None:
        stmt = (
            select(Reservation)
            .options(
                joinedload(Reservation.seat).joinedload(Seat.zone).joinedload(Zone.branch),
            )
            .where(Reservation.id == reservation_id)
        )
        return self.db.scalar(stmt)

    def list_by_user(self, user_id: int) -> list[Reservation]:
        stmt = select(Reservation).where(Reservation.user_id == user_id).order_by(Reservation.id)
        return list(self.db.scalars(stmt))

    def list_all(self) -> list[Reservation]:
        return list(self.db.scalars(select(Reservation).order_by(Reservation.id)))

    def get_club_id(self, reservation_id: int) -> int | None:
        stmt = (
            select(Branch.club_id)
            .select_from(Reservation)
            .join(Seat, Reservation.seat_id == Seat.id)
            .join(Zone, Seat.zone_id == Zone.id)
            .join(Branch, Zone.branch_id == Branch.id)
            .where(Reservation.id == reservation_id)
        )
        return self.db.scalar(stmt)

    def list_booked_intervals_for_day(self, *, seat_id: int, target_date: date) -> list[tuple[datetime, datetime]]:
        day_start = datetime.combine(target_date, time.min, tzinfo=timezone.utc)
        day_end = datetime.combine(target_date, time.max, tzinfo=timezone.utc)
        stmt = select(Reservation.start_at, Reservation.end_at).where(
            Reservation.seat_id == seat_id,
            Reservation.status.in_(ACTIVE_RESERVATION_STATUSES),
            Reservation.start_at < day_end,
            Reservation.end_at > day_start,
            Reservation.cancelled_at.is_(None),
        )
        return list(self.db.execute(stmt).all())

    def has_overlap(self, *, seat_id: int, start_at, end_at) -> bool:
        stmt = select(Reservation.id).where(
            and_(
                Reservation.seat_id == seat_id,
                Reservation.status.in_(ACTIVE_RESERVATION_STATUSES),
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
