from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.seat_status_history import SeatStatusHistory


class SeatStatusHistoryRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_for_seat(self, seat_id: int) -> list[SeatStatusHistory]:
        stmt = (
            select(SeatStatusHistory)
            .where(SeatStatusHistory.seat_id == seat_id)
            .order_by(SeatStatusHistory.id.desc())
        )
        return list(self.db.scalars(stmt))

    def create(
        self,
        *,
        seat_id: int,
        changed_by_user_id: int,
        from_status: str,
        to_status: str,
        reason: str | None,
    ) -> SeatStatusHistory:
        item = SeatStatusHistory(
            seat_id=seat_id,
            changed_by_user_id=changed_by_user_id,
            from_status=from_status,
            to_status=to_status,
            reason=reason,
        )
        self.db.add(item)
        self.db.flush()
        return item
