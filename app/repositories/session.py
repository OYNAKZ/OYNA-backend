from __future__ import annotations

from datetime import date, datetime, time, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.constants import SessionStatus
from app.models.session import Session as SessionModel
from app.schemas.session import SessionCreate


class SessionRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, session_id: int) -> SessionModel | None:
        return self.db.get(SessionModel, session_id)

    def get_by_reservation_id(self, reservation_id: int) -> SessionModel | None:
        stmt = select(SessionModel).where(SessionModel.reservation_id == reservation_id)
        return self.db.scalar(stmt)

    def get_active_by_reservation_id(self, reservation_id: int) -> SessionModel | None:
        stmt = select(SessionModel).where(
            SessionModel.reservation_id == reservation_id,
            SessionModel.status == SessionStatus.ACTIVE.value,
        )
        return self.db.scalar(stmt)

    def get_active_by_seat_id(self, seat_id: int) -> SessionModel | None:
        stmt = select(SessionModel).where(
            SessionModel.seat_id == seat_id,
            SessionModel.status == SessionStatus.ACTIVE.value,
        )
        return self.db.scalar(stmt)

    def list_active(self) -> list[SessionModel]:
        stmt = select(SessionModel).where(SessionModel.status == SessionStatus.ACTIVE.value).order_by(SessionModel.id)
        return list(self.db.scalars(stmt))

    def list_all(self) -> list[SessionModel]:
        return list(self.db.scalars(select(SessionModel).order_by(SessionModel.id)))

    def list_by_user(self, user_id: int) -> list[SessionModel]:
        stmt = select(SessionModel).where(SessionModel.user_id == user_id).order_by(SessionModel.id)
        return list(self.db.scalars(stmt))

    def list_booked_intervals_for_day(self, *, seat_id: int, target_date: date) -> list[tuple[datetime, datetime]]:
        day_start = datetime.combine(target_date, time.min, tzinfo=timezone.utc)
        day_end = datetime.combine(target_date, time.max, tzinfo=timezone.utc)
        stmt = select(SessionModel.started_at, SessionModel.planned_end_at, SessionModel.ended_at).where(
            SessionModel.seat_id == seat_id,
            SessionModel.status != SessionStatus.CANCELLED.value,
            SessionModel.started_at < day_end,
            SessionModel.planned_end_at > day_start,
        )
        rows = self.db.execute(stmt).all()
        return [(started_at, ended_at or planned_end_at) for started_at, planned_end_at, ended_at in rows]

    def create(self, payload: SessionCreate) -> SessionModel:
        item = SessionModel(**payload.model_dump())
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    def update(self, session: SessionModel, **changes) -> SessionModel:
        for field, value in changes.items():
            setattr(session, field, value)
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        return session


def list_items(db: Session) -> list[SessionModel]:
    return SessionRepository(db).list_all()


def create_item(db: Session, payload: SessionCreate) -> SessionModel:
    return SessionRepository(db).create(payload)
