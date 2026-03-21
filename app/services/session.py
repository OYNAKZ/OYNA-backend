from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.constants import STAFF_ROLES, ReservationStatus
from app.models.reservation import Reservation
from app.models.user import User
from app.repositories import session as repository
from app.repositories.session import SessionRepository
from app.schemas.session import SessionCreate, SessionRead


def list_sessions(db: Session, current_user: User) -> list[SessionRead]:
    repo = SessionRepository(db)
    if current_user.role in STAFF_ROLES:
        return repo.list_all()
    return repo.list_by_user(current_user.id)


def create_session(db: Session, payload: SessionCreate) -> SessionRead:
    reservation = db.get(Reservation, payload.reservation_id)
    if reservation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reservation not found")

    if reservation.status not in (ReservationStatus.CONFIRMED.value, ReservationStatus.CHECKED_IN.value):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Reservation is not eligible for session start",
        )

    if payload.started_at >= payload.planned_end_at:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="planned_end_at must be after started_at",
        )
    if payload.ended_at is not None and payload.ended_at < payload.started_at:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="ended_at must not be earlier than started_at",
        )
    if payload.seat_id is not None and payload.seat_id != reservation.seat_id:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Session seat must match reservation seat")
    if payload.user_id is not None and payload.user_id != reservation.user_id:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Session user must match reservation user")

    if SessionRepository(db).get_by_reservation_id(payload.reservation_id) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Session already exists")

    create_payload = SessionCreate(
        reservation_id=reservation.id,
        seat_id=reservation.seat_id,
        user_id=reservation.user_id,
        started_at=payload.started_at,
        planned_end_at=payload.planned_end_at,
        ended_at=payload.ended_at,
        status=payload.status,
    )
    return repository.create_item(db, create_payload)
