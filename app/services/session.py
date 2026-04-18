from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.constants import ReservationStatus, SeatOperationalStatus, UserRole
from app.models.user import User
from app.repositories import session as repository
from app.repositories.reservation import ReservationRepository
from app.repositories.session import SessionRepository
from app.schemas.session import SessionCreate, SessionRead
from app.services.lifecycle import ensure_reservation_can_start_session, ensure_session_creation_status_allowed
from app.services.policies import ensure_can_operate_reservation, ensure_staff_scope_access, reservation_scope_clause


def list_sessions(db: Session, current_user: User) -> list[SessionRead]:
    repo = SessionRepository(db)
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


def create_session(db: Session, payload: SessionCreate, current_user: User) -> SessionRead:
    ensure_staff_scope_access(db, current_user)
    reservation = ReservationRepository(db).get_by_id_with_location(payload.reservation_id)
    if reservation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reservation not found")
    ensure_can_operate_reservation(db, current_user, reservation)
    ensure_session_creation_status_allowed(payload.status)

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

    ensure_reservation_can_start_session(
        reservation,
        now=payload.started_at,
        seat_status=reservation.seat.operational_status if reservation.seat is not None else SeatOperationalStatus.AVAILABLE.value,
        has_session=SessionRepository(db).get_by_reservation_id(payload.reservation_id) is not None,
        has_active_session_for_seat=SessionRepository(db).get_active_by_seat_id(reservation.seat_id) is not None,
    )

    create_payload = SessionCreate(
        reservation_id=reservation.id,
        seat_id=reservation.seat_id,
        user_id=reservation.user_id,
        started_at=payload.started_at,
        planned_end_at=payload.planned_end_at,
        ended_at=payload.ended_at,
        status=payload.status,
    )
    session = repository.create_item(db, create_payload)
    reservation.status = ReservationStatus.SESSION_STARTED.value
    db.add(reservation)
    if reservation.seat is not None:
        reservation.seat.operational_status = SeatOperationalStatus.OCCUPIED.value
        reservation.seat.is_active = True
        reservation.seat.is_maintenance = False
        db.add(reservation.seat)
    db.commit()
    db.refresh(session)
    return session
