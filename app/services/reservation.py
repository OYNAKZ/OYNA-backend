from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.constants import STAFF_ROLES, ReservationStatus
from app.models.seat import Seat
from app.models.user import User
from app.repositories import reservation as repository
from app.repositories.reservation import ReservationRepository
from app.schemas.reservation import ReservationCreate, ReservationRead


def list_reservations(db: Session, current_user: User) -> list[ReservationRead]:
    repo = ReservationRepository(db)
    if current_user.role in STAFF_ROLES:
        return repo.list_all()
    return repo.list_by_user(current_user.id)


def create_reservation(db: Session, payload: ReservationCreate, current_user: User) -> ReservationRead:
    if payload.end_at <= payload.start_at:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="end_at must be after start_at")

    if payload.user_id is not None and payload.user_id != current_user.id and current_user.role not in STAFF_ROLES:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot create reservations for another user")

    user_id = payload.user_id or current_user.id
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    seat = db.get(Seat, payload.seat_id)
    if seat is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Seat not found")
    if not seat.is_active or seat.is_maintenance:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Seat is not available for reservation")

    repo = ReservationRepository(db)
    if repo.has_overlap(seat_id=payload.seat_id, start_at=payload.start_at, end_at=payload.end_at):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Seat already reserved for this time range")

    create_payload = ReservationCreate(
        seat_id=payload.seat_id,
        user_id=user_id,
        start_at=payload.start_at,
        end_at=payload.end_at,
        status=payload.status or ReservationStatus.CONFIRMED.value,
        expires_at=payload.expires_at,
        cancelled_at=payload.cancelled_at,
    )
    return repository.create_item(db, create_payload)
