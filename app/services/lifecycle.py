from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.constants import ReservationStatus, SeatOperationalStatus, SessionStatus
from app.models import Reservation, Seat
from app.repositories.reservation import ReservationRepository
from app.repositories.session import SessionRepository


def as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def ensure_reservation_creation_status_allowed(status_value: str) -> None:
    allowed = {ReservationStatus.CREATED.value, ReservationStatus.CONFIRMED.value}
    if status_value not in allowed:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Reservation creation status is not allowed",
        )


def ensure_reservation_can_check_in(reservation: Reservation, *, now: datetime, has_session: bool) -> None:
    if reservation.status == ReservationStatus.CHECKED_IN.value:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Reservation already checked in")
    if reservation.status == ReservationStatus.SESSION_STARTED.value:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Reservation already converted to session")
    if reservation.status == ReservationStatus.CANCELLED.value:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Reservation is cancelled")
    if reservation.status == ReservationStatus.EXPIRED.value:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Reservation is expired")
    if reservation.status == ReservationStatus.NO_SHOW.value:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Reservation is marked as no-show")
    if reservation.status == ReservationStatus.COMPLETED.value:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Reservation is already completed")
    if reservation.status != ReservationStatus.CONFIRMED.value:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Reservation is not eligible for check-in")

    expires_at = as_utc(reservation.expires_at) if reservation.expires_at is not None else None
    if expires_at is not None and expires_at <= now:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Reservation is expired")
    if has_session:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Session already exists for reservation")


def ensure_reservation_can_start_session(
    reservation: Reservation,
    *,
    now: datetime,
    seat_status: str,
    has_session: bool,
    has_active_session_for_seat: bool,
) -> None:
    if has_session:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Session already exists")
    if reservation.status not in (ReservationStatus.CHECKED_IN.value, ReservationStatus.CONFIRMED.value):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Reservation is not eligible for session start",
        )
    expires_at = as_utc(reservation.expires_at) if reservation.expires_at is not None else None
    if reservation.status == ReservationStatus.CONFIRMED.value and expires_at is not None and expires_at <= now:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Reservation is expired")
    if as_utc(reservation.end_at) <= now:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Reservation has already ended")
    if seat_status in (SeatOperationalStatus.MAINTENANCE.value, SeatOperationalStatus.OFFLINE.value):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Seat is not available for session start")
    if has_active_session_for_seat:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Seat already has an active session")


def ensure_reservation_can_cancel(
    reservation: Reservation,
    *,
    now: datetime,
    has_active_session: bool,
) -> None:
    if reservation.status == ReservationStatus.CANCELLED.value or reservation.cancelled_at is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Reservation is already cancelled")
    if reservation.status == ReservationStatus.SESSION_STARTED.value:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Reservation has already started a session")
    if reservation.status == ReservationStatus.COMPLETED.value:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Reservation is already completed")
    if reservation.status == ReservationStatus.EXPIRED.value:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Reservation is expired")
    if reservation.status == ReservationStatus.NO_SHOW.value:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Reservation is marked as no-show")
    if has_active_session:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Active session prevents cancellation")

    reservation_start = as_utc(reservation.start_at)
    if reservation_start - now < timedelta(minutes=15):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cancellation window has closed")


def ensure_session_creation_status_allowed(status_value: str) -> None:
    if status_value != SessionStatus.ACTIVE.value:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="New sessions must start as active")


def ensure_session_can_finish(current_status: str) -> None:
    if current_status != SessionStatus.ACTIVE.value:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Session is not active")


def ensure_manual_seat_status_change_allowed(db: Session, seat: Seat, *, new_status: str) -> None:
    if new_status == seat.operational_status:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Seat is already in requested status")
    if new_status in (SeatOperationalStatus.RESERVED.value, SeatOperationalStatus.OCCUPIED.value):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Seat status is managed by reservation/session lifecycle",
        )

    active_session = SessionRepository(db).get_active_by_seat_id(seat.id)
    if active_session is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Active session prevents manual seat status changes")

    active_reservations = ReservationRepository(db).has_active_for_seat(seat_id=seat.id)
    if active_reservations and new_status in (
        SeatOperationalStatus.AVAILABLE.value,
        SeatOperationalStatus.MAINTENANCE.value,
        SeatOperationalStatus.OFFLINE.value,
    ):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Active reservations prevent seat status change")


def sync_seat_operational_status(
    db: Session,
    seat: Seat,
    *,
    exclude_reservation_id: int | None = None,
    exclude_session_id: int | None = None,
) -> None:
    active_session = SessionRepository(db).get_active_by_seat_id(seat.id, exclude_session_id=exclude_session_id)
    if active_session is not None:
        seat.operational_status = SeatOperationalStatus.OCCUPIED.value
        seat.is_active = True
        seat.is_maintenance = False
        return

    if seat.operational_status in (SeatOperationalStatus.MAINTENANCE.value, SeatOperationalStatus.OFFLINE.value):
        seat.is_active = seat.operational_status != SeatOperationalStatus.OFFLINE.value
        seat.is_maintenance = seat.operational_status == SeatOperationalStatus.MAINTENANCE.value
        return

    has_active_reservations = ReservationRepository(db).has_active_for_seat(
        seat_id=seat.id,
        exclude_reservation_id=exclude_reservation_id,
    )
    if has_active_reservations:
        seat.operational_status = SeatOperationalStatus.RESERVED.value
    else:
        seat.operational_status = SeatOperationalStatus.AVAILABLE.value

    seat.is_active = True
    seat.is_maintenance = False
