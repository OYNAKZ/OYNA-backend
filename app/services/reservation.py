from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.constants import SessionStatus, STAFF_ROLES, ReservationStatus, UserRole
from app.models.seat import Seat
from app.models.user import User
from app.repositories import reservation as repository
from app.repositories.reservation import ReservationRepository
from app.repositories.session import SessionRepository
from app.schemas.reservation import ReservationCreate, ReservationDetailRead, ReservationRead


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


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


def _ensure_reservation_access(
    repo: ReservationRepository,
    reservation_id: int,
    current_user: User,
) -> int:
    reservation = repo.get_by_id(reservation_id)
    if reservation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reservation not found")

    if current_user.role == UserRole.USER.value and reservation.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Reservation is not accessible")

    if current_user.role == UserRole.CLUB_ADMIN.value:
        if current_user.club_id is None:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Reservation is not accessible")
        reservation_club_id = repo.get_club_id(reservation_id)
        if reservation_club_id != current_user.club_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Reservation is not accessible")

    return reservation.id


def get_reservation_detail(db: Session, reservation_id: int, current_user: User) -> ReservationDetailRead:
    repo = ReservationRepository(db)
    _ensure_reservation_access(repo, reservation_id, current_user)

    reservation = repo.get_by_id_with_location(reservation_id)
    if reservation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reservation not found")
    return ReservationDetailRead.model_validate(reservation)


def cancel_reservation(db: Session, reservation_id: int, current_user: User) -> ReservationRead:
    repo = ReservationRepository(db)
    reservation_id = _ensure_reservation_access(repo, reservation_id, current_user)
    reservation = repo.get_by_id(reservation_id)
    if reservation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reservation not found")

    if reservation.status == ReservationStatus.CANCELLED.value or reservation.cancelled_at is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Reservation is already cancelled")

    now = datetime.now(timezone.utc)
    reservation_start = _as_utc(reservation.start_at)
    if reservation_start - now < timedelta(minutes=15):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cancellation window has closed")

    active_session = SessionRepository(db).get_active_by_reservation_id(reservation_id)
    if active_session is not None and active_session.status == SessionStatus.ACTIVE.value:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Active session prevents cancellation")

    return ReservationRead.model_validate(
        repo.update(
            reservation,
            status=ReservationStatus.CANCELLED.value,
            cancelled_at=now,
        )
    )
