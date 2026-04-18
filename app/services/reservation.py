from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.constants import STAFF_ROLES, ReservationStatus, SeatOperationalStatus, SessionStatus, UserRole
from app.models.seat import Seat
from app.models.user import User
from app.repositories import reservation as repository
from app.repositories.reservation import ReservationRepository
from app.repositories.session import SessionRepository
from app.schemas.reservation import ReservationCreate, ReservationDetailRead, ReservationHoldCreate, ReservationRead
from app.services.availability import check_seat_availability, cleanup_expired_holds, normalize_interval
from app.services.lifecycle import (
    as_utc,
    ensure_reservation_can_cancel,
    ensure_reservation_creation_status_allowed,
    sync_seat_operational_status,
)
from app.services.policies import (
    ensure_can_operate_reservation,
    ensure_can_operate_seat,
    ensure_staff_scope_access,
    reservation_scope_clause,
)


def list_reservations(db: Session, current_user: User) -> list[ReservationRead]:
    cleanup_expired_holds(db, now=datetime.now(timezone.utc))
    repo = ReservationRepository(db)
    if current_user.role == UserRole.PLATFORM_ADMIN.value:
        return repo.list_all()
    if current_user.role == UserRole.OWNER.value:
        ensure_staff_scope_access(db, current_user)
        club_ids, branch_ids, _ = reservation_scope_clause(db, current_user)
        return [
            item
            for item in repo.list_all_with_location()
            if item.seat is not None
            and item.seat.branch is not None
            and item.seat.branch.club_id in club_ids
            and (not branch_ids or item.seat.branch.id in branch_ids)
        ]
    if current_user.role == UserRole.CLUB_ADMIN.value:
        ensure_staff_scope_access(db, current_user)
        club_ids, branch_ids, _ = reservation_scope_clause(db, current_user)
        return [
            item
            for item in repo.list_all_with_location()
            if item.seat is not None
            and item.seat.branch is not None
            and item.seat.branch.club_id in club_ids
            and (not branch_ids or item.seat.branch.id in branch_ids)
        ]
    return repo.list_by_user(current_user.id)


def create_reservation(db: Session, payload: ReservationCreate, current_user: User) -> ReservationRead:
    cleanup_expired_holds(db, now=datetime.now(timezone.utc))
    start_at, end_at = normalize_interval(payload.start_at, payload.end_at)

    if payload.user_id is not None and payload.user_id != current_user.id and current_user.role not in STAFF_ROLES:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot create reservations for another user")

    user_id = payload.user_id or current_user.id
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    seat = db.get(Seat, payload.seat_id)
    if seat is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Seat not found")
    if current_user.role in STAFF_ROLES:
        ensure_staff_scope_access(db, current_user)
        ensure_can_operate_seat(db, current_user, seat)

    availability = check_seat_availability(db, seat_id=payload.seat_id, start_at=start_at, end_at=end_at)
    if not availability.is_available:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=availability.reason or "Seat is unavailable")

    status_value = payload.status.value if hasattr(payload.status, "value") else str(payload.status)
    ensure_reservation_creation_status_allowed(status_value)

    create_payload = ReservationCreate(
        seat_id=payload.seat_id,
        user_id=user_id,
        start_at=start_at,
        end_at=end_at,
        status=status_value,
        idempotency_key=payload.idempotency_key,
        expires_at=payload.expires_at,
        cancelled_at=payload.cancelled_at,
    )
    reservation = repository.create_item(db, create_payload)
    if seat.operational_status == SeatOperationalStatus.AVAILABLE.value:
        seat.operational_status = SeatOperationalStatus.RESERVED.value
        db.add(seat)
        db.commit()
    return reservation


def create_reservation_hold(db: Session, payload: ReservationHoldCreate, current_user: User) -> ReservationRead:
    cleanup_expired_holds(db, now=datetime.now(timezone.utc))
    start_at, end_at = normalize_interval(payload.start_at, payload.end_at)

    if payload.user_id is not None and payload.user_id != current_user.id and current_user.role not in STAFF_ROLES:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot create reservations for another user")

    user_id = payload.user_id or current_user.id
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    seat = db.get(Seat, payload.seat_id)
    if seat is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Seat not found")
    if current_user.role in STAFF_ROLES:
        ensure_staff_scope_access(db, current_user)
        ensure_can_operate_seat(db, current_user, seat)

    repo = ReservationRepository(db)
    existing = repo.get_by_user_and_idempotency_key(user_id=user_id, idempotency_key=payload.idempotency_key)
    if existing is not None:
        if (
            existing.seat_id != payload.seat_id
            or as_utc(existing.start_at) != start_at
            or as_utc(existing.end_at) != end_at
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Idempotency key already used for different reservation intent",
            )
        return ReservationRead.model_validate(existing)

    availability = check_seat_availability(db, seat_id=payload.seat_id, start_at=start_at, end_at=end_at)
    if not availability.is_available:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=availability.reason or "Seat is unavailable")

    ttl_seconds = payload.hold_ttl_seconds or settings.reservation_hold_ttl_seconds
    if ttl_seconds <= 0:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="hold_ttl_seconds must be positive")
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)

    try:
        reservation = repository.create_item(
            db,
            ReservationCreate(
                seat_id=payload.seat_id,
                user_id=user_id,
                start_at=start_at,
                end_at=end_at,
                status=ReservationStatus.PENDING_PAYMENT.value,
                idempotency_key=payload.idempotency_key,
                expires_at=expires_at,
            ),
        )
    except IntegrityError:
        db.rollback()
        existing = repo.get_by_user_and_idempotency_key(user_id=user_id, idempotency_key=payload.idempotency_key)
        if existing is None:
            raise
        if (
            existing.seat_id != payload.seat_id
            or as_utc(existing.start_at) != start_at
            or as_utc(existing.end_at) != end_at
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Idempotency key already used for different reservation intent",
            )
        return ReservationRead.model_validate(existing)
    if seat.operational_status == SeatOperationalStatus.AVAILABLE.value:
        seat.operational_status = SeatOperationalStatus.RESERVED.value
        db.add(seat)
        db.commit()
    return ReservationRead.model_validate(reservation)


def confirm_reservation_hold(db: Session, reservation_id: int, current_user: User) -> ReservationRead:
    cleanup_expired_holds(db, now=datetime.now(timezone.utc))
    repo = ReservationRepository(db)
    scoped_reservation_id = _ensure_reservation_access(repo, reservation_id, current_user)
    return ReservationRead.model_validate(confirm_reservation_hold_for_payment(db, reservation_id=scoped_reservation_id))


def confirm_reservation_hold_for_payment(db: Session, *, reservation_id: int):
    cleanup_expired_holds(db, now=datetime.now(timezone.utc))
    repo = ReservationRepository(db)
    reservation = repo.get_by_id(reservation_id)
    if reservation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reservation not found")

    if reservation.status == ReservationStatus.CONFIRMED.value:
        return reservation
    if reservation.status == ReservationStatus.EXPIRED.value:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Reservation hold has expired")
    if reservation.status != ReservationStatus.PENDING_PAYMENT.value:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Reservation is not pending payment")

    now = datetime.now(timezone.utc)
    expires_at = as_utc(reservation.expires_at) if reservation.expires_at is not None else None
    if expires_at is not None and expires_at <= now:
        repo.update(reservation, status=ReservationStatus.EXPIRED.value)
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Reservation hold has expired")

    return repo.update(
        reservation,
        status=ReservationStatus.CONFIRMED.value,
        expires_at=None,
    )


def _ensure_reservation_access(
    repo: ReservationRepository,
    reservation_id: int,
    current_user: User,
) -> int:
    reservation = repo.get_by_id(reservation_id)
    if reservation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reservation not found")

    if current_user.role == UserRole.USER.value:
        if reservation.user_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Reservation is not accessible")
        return reservation.id

    if current_user.role in STAFF_ROLES:
        reservation_with_scope = repo.get_by_id_with_location(reservation_id)
        if reservation_with_scope is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reservation not found")
        ensure_can_operate_reservation(db=repo.db, user=current_user, reservation=reservation_with_scope)
    return reservation.id


def get_reservation_detail(db: Session, reservation_id: int, current_user: User) -> ReservationDetailRead:
    cleanup_expired_holds(db, now=datetime.now(timezone.utc))
    repo = ReservationRepository(db)
    _ensure_reservation_access(repo, reservation_id, current_user)

    reservation = repo.get_by_id_with_location(reservation_id)
    if reservation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reservation not found")
    return ReservationDetailRead.model_validate(reservation)


def cancel_reservation(db: Session, reservation_id: int, current_user: User) -> ReservationRead:
    cleanup_expired_holds(db, now=datetime.now(timezone.utc))
    repo = ReservationRepository(db)
    reservation_id = _ensure_reservation_access(repo, reservation_id, current_user)
    reservation = repo.get_by_id(reservation_id)
    if reservation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reservation not found")

    now = datetime.now(timezone.utc)
    active_session = SessionRepository(db).get_active_by_reservation_id(reservation_id)
    ensure_reservation_can_cancel(
        reservation,
        now=now,
        has_active_session=active_session is not None and active_session.status == SessionStatus.ACTIVE.value,
    )

    updated = repo.update(
        reservation,
        status=ReservationStatus.CANCELLED.value,
        cancelled_at=now,
    )
    seat = reservation.seat
    if seat is not None:
        sync_seat_operational_status(db, seat, exclude_reservation_id=reservation.id)
        db.add(seat)
        db.commit()
    return ReservationRead.model_validate(updated)
