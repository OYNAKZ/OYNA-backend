from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.core.constants import ReservationStatus, SeatOperationalStatus, SessionStatus, UserRole
from app.models import Branch, Reservation, Seat, User, Zone
from app.models import Session as SessionModel
from app.repositories.reservation import ReservationRepository
from app.repositories.seat_status_history import SeatStatusHistoryRepository
from app.repositories.session import SessionRepository
from app.schemas.common import PaginatedResponse
from app.schemas.operations import (
    ClubOperationsSummaryRead,
    ClubZoneLoadRead,
    ReservationOperationsRead,
    SessionOperationsRead,
)
from app.schemas.seat import SeatStatusHistoryRead
from app.services.policies import (
    ensure_active_scope_assignment,
    ensure_can_operate_reservation,
    ensure_can_operate_seat,
)


def _reservation_stmt():
    return (
        select(Reservation)
        .options(joinedload(Reservation.seat).joinedload(Seat.zone).joinedload(Zone.branch))
        .join(Seat, Reservation.seat_id == Seat.id)
        .join(Zone, Seat.zone_id == Zone.id)
        .join(Branch, Zone.branch_id == Branch.id)
    )


def _session_stmt():
    return (
        select(SessionModel)
        .options(joinedload(SessionModel.seat).joinedload(Seat.zone).joinedload(Zone.branch))
        .join(Seat, SessionModel.seat_id == Seat.id)
        .join(Zone, Seat.zone_id == Zone.id)
        .join(Branch, Zone.branch_id == Branch.id)
    )


def _allowed_branch_clause(db: Session, current_user: User):
    from app.services.policies import reservation_scope_clause

    club_ids, branch_ids, allow_all = reservation_scope_clause(db, current_user)
    if current_user.role == UserRole.USER.value:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
    ensure_active_scope_assignment(db, current_user)
    return club_ids, branch_ids, allow_all


def _apply_scope(stmt, *, club_ids: set[int], branch_ids: set[int], allow_all: bool):
    if allow_all:
        return stmt
    stmt = stmt.where(Branch.club_id.in_(club_ids))
    if branch_ids:
        stmt = stmt.where(Branch.id.in_(branch_ids))
    return stmt


def list_operational_reservations(
    db: Session,
    current_user: User,
    *,
    branch_id: int | None,
    zone_id: int | None,
    seat_id: int | None,
    status_value: str | None,
    range_start: datetime | None,
    range_end: datetime | None,
    page: int,
    page_size: int,
) -> PaginatedResponse[ReservationOperationsRead]:
    club_ids, branch_ids, allow_all = _allowed_branch_clause(db, current_user)
    stmt = _apply_scope(_reservation_stmt(), club_ids=club_ids, branch_ids=branch_ids, allow_all=allow_all)

    if branch_id is not None:
        stmt = stmt.where(Branch.id == branch_id)
    if zone_id is not None:
        stmt = stmt.where(Zone.id == zone_id)
    if seat_id is not None:
        stmt = stmt.where(Seat.id == seat_id)
    if status_value is not None:
        stmt = stmt.where(Reservation.status == status_value)
    if range_start is not None:
        stmt = stmt.where(Reservation.end_at >= range_start)
    if range_end is not None:
        stmt = stmt.where(Reservation.start_at <= range_end)

    count_stmt = select(func.count()).select_from(stmt.order_by(None).subquery())
    total = db.scalar(count_stmt) or 0
    rows = (
        db.scalars(stmt.order_by(Reservation.start_at).offset((page - 1) * page_size).limit(page_size)).unique().all()
    )
    return PaginatedResponse[ReservationOperationsRead](items=rows, total=total, page=page, page_size=page_size)


def list_operational_sessions(
    db: Session,
    current_user: User,
    *,
    active_only: bool,
    branch_id: int | None,
    page: int,
    page_size: int,
) -> PaginatedResponse[SessionOperationsRead]:
    club_ids, branch_ids, allow_all = _allowed_branch_clause(db, current_user)
    stmt = _apply_scope(_session_stmt(), club_ids=club_ids, branch_ids=branch_ids, allow_all=allow_all)
    if active_only:
        stmt = stmt.where(SessionModel.status == SessionStatus.ACTIVE.value)
    if branch_id is not None:
        stmt = stmt.where(Branch.id == branch_id)

    total = db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0
    rows = (
        db.scalars(stmt.order_by(SessionModel.started_at.desc()).offset((page - 1) * page_size).limit(page_size))
        .unique()
        .all()
    )
    return PaginatedResponse[SessionOperationsRead](items=rows, total=total, page=page, page_size=page_size)


def check_in_reservation(db: Session, reservation_id: int, current_user: User) -> ReservationOperationsRead:
    ensure_active_scope_assignment(db, current_user)
    reservation = db.scalar(_reservation_stmt().where(Reservation.id == reservation_id))
    if reservation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reservation not found")
    ensure_can_operate_reservation(db, current_user, reservation)

    now = datetime.now(timezone.utc)
    if reservation.status == ReservationStatus.CHECKED_IN.value:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Reservation already checked in")
    if reservation.status == ReservationStatus.SESSION_STARTED.value:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Reservation already converted to session")
    if reservation.status == ReservationStatus.CANCELLED.value:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Reservation is cancelled")
    if reservation.expires_at is not None and reservation.expires_at <= now:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Reservation is expired")

    window_start = reservation.start_at - timedelta(minutes=30)
    window_end = reservation.end_at
    if now < window_start or now > window_end:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Reservation is outside check-in window")
    if SessionRepository(db).get_by_reservation_id(reservation.id) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Session already exists for reservation")

    updated = ReservationRepository(db).update(reservation, status=ReservationStatus.CHECKED_IN.value)
    return ReservationOperationsRead.model_validate(updated)


def start_session_from_reservation(db: Session, reservation_id: int, current_user: User) -> SessionOperationsRead:
    ensure_active_scope_assignment(db, current_user)
    reservation = db.scalar(_reservation_stmt().where(Reservation.id == reservation_id))
    if reservation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reservation not found")
    ensure_can_operate_reservation(db, current_user, reservation)

    seat = reservation.seat
    if reservation.status not in (ReservationStatus.CHECKED_IN.value, ReservationStatus.CONFIRMED.value):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Reservation is not eligible for session start",
        )
    if seat.operational_status in (SeatOperationalStatus.MAINTENANCE.value, SeatOperationalStatus.OFFLINE.value):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Seat is not available for session start")
    if SessionRepository(db).get_by_reservation_id(reservation.id) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Session already exists")
    if SessionRepository(db).get_active_by_seat_id(seat.id) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Seat already has an active session")

    now = datetime.now(timezone.utc)
    session = SessionModel(
        reservation_id=reservation.id,
        seat_id=reservation.seat_id,
        user_id=reservation.user_id,
        started_at=now,
        planned_end_at=reservation.end_at,
        status=SessionStatus.ACTIVE.value,
    )
    db.add(session)
    reservation.status = ReservationStatus.SESSION_STARTED.value
    seat.operational_status = SeatOperationalStatus.OCCUPIED.value
    seat.is_active = True
    seat.is_maintenance = False
    db.add_all([reservation, seat, session])
    db.commit()
    db.refresh(session)
    return SessionOperationsRead.model_validate(session)


def finish_session(db: Session, session_id: int, current_user: User) -> SessionOperationsRead:
    ensure_active_scope_assignment(db, current_user)
    session = db.scalar(_session_stmt().where(SessionModel.id == session_id))
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    ensure_can_operate_seat(db, current_user, session.seat)

    if session.status != SessionStatus.ACTIVE.value:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Session is already finished")

    now = datetime.now(timezone.utc)
    session.status = SessionStatus.FINISHED.value
    session.ended_at = now
    seat = session.seat
    if seat.operational_status == SeatOperationalStatus.OCCUPIED.value:
        seat.operational_status = SeatOperationalStatus.AVAILABLE.value
    seat.is_active = seat.operational_status != SeatOperationalStatus.OFFLINE.value
    seat.is_maintenance = seat.operational_status == SeatOperationalStatus.MAINTENANCE.value
    db.add_all([session, seat])
    db.commit()
    db.refresh(session)
    return SessionOperationsRead.model_validate(session)


def update_seat_operational_status(
    db: Session,
    seat_id: int,
    *,
    new_status: str,
    reason: str | None,
    current_user: User,
) -> SeatStatusHistoryRead:
    ensure_active_scope_assignment(db, current_user)
    seat = db.scalar(select(Seat).options(joinedload(Seat.zone).joinedload(Zone.branch)).where(Seat.id == seat_id))
    if seat is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Seat not found")
    ensure_can_operate_seat(db, current_user, seat)

    if new_status not in {item.value for item in SeatOperationalStatus}:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid seat status")
    active_session = SessionRepository(db).get_active_by_seat_id(seat.id)
    if new_status == SeatOperationalStatus.AVAILABLE.value and active_session is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Active session prevents seat release")
    if new_status == SeatOperationalStatus.MAINTENANCE.value and active_session is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Active session prevents maintenance mode")

    previous_status = seat.operational_status
    seat.operational_status = new_status
    seat.is_active = new_status not in (SeatOperationalStatus.OFFLINE.value,)
    seat.is_maintenance = new_status == SeatOperationalStatus.MAINTENANCE.value
    db.add(seat)
    history = SeatStatusHistoryRepository(db).create(
        seat_id=seat.id,
        changed_by_user_id=current_user.id,
        from_status=previous_status,
        to_status=new_status,
        reason=reason,
    )
    db.commit()
    db.refresh(history)
    return SeatStatusHistoryRead.model_validate(history)


def get_seat_status_history(db: Session, seat_id: int, current_user: User) -> list[SeatStatusHistoryRead]:
    ensure_active_scope_assignment(db, current_user)
    seat = db.scalar(select(Seat).options(joinedload(Seat.zone).joinedload(Zone.branch)).where(Seat.id == seat_id))
    if seat is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Seat not found")
    ensure_can_operate_seat(db, current_user, seat)
    return [
        SeatStatusHistoryRead.model_validate(item) for item in SeatStatusHistoryRepository(db).list_for_seat(seat_id)
    ]


def get_live_club_summary(db: Session, current_user: User, branch_id: int | None) -> ClubOperationsSummaryRead:
    club_ids, branch_ids, allow_all = _allowed_branch_clause(db, current_user)
    seat_stmt = select(Seat).options(joinedload(Seat.zone).joinedload(Zone.branch)).join(Zone).join(Branch)
    seat_stmt = _apply_scope(seat_stmt, club_ids=club_ids, branch_ids=branch_ids, allow_all=allow_all)
    if branch_id is not None:
        seat_stmt = seat_stmt.where(Branch.id == branch_id)

    seats = db.scalars(seat_stmt).unique().all()
    if not seats:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Club scope not found")

    seat_ids = [seat.id for seat in seats]
    active_reservations = (
        db.scalar(
            select(func.count())
            .select_from(Reservation)
            .where(
                Reservation.seat_id.in_(seat_ids),
                Reservation.status.in_(
                    [
                        ReservationStatus.CONFIRMED.value,
                        ReservationStatus.CHECKED_IN.value,
                        ReservationStatus.SESSION_STARTED.value,
                    ]
                ),
            )
        )
        or 0
    )
    active_sessions = (
        db.scalar(
            select(func.count())
            .select_from(SessionModel)
            .where(
                SessionModel.seat_id.in_(seat_ids),
                SessionModel.status == SessionStatus.ACTIVE.value,
            )
        )
        or 0
    )

    zone_map: dict[int, ClubZoneLoadRead] = {}
    for seat in seats:
        zone = seat.zone
        current = zone_map.get(zone.id)
        if current is None:
            current = ClubZoneLoadRead(
                zone=zone,
                total_seats=0,
                occupied_seats=0,
                reserved_seats=0,
                maintenance_seats=0,
                offline_seats=0,
                available_seats=0,
            )
            zone_map[zone.id] = current
        current.total_seats += 1
        if seat.operational_status == SeatOperationalStatus.OCCUPIED.value:
            current.occupied_seats += 1
        elif seat.operational_status == SeatOperationalStatus.RESERVED.value:
            current.reserved_seats += 1
        elif seat.operational_status == SeatOperationalStatus.MAINTENANCE.value:
            current.maintenance_seats += 1
        elif seat.operational_status == SeatOperationalStatus.OFFLINE.value:
            current.offline_seats += 1
        else:
            current.available_seats += 1

    return ClubOperationsSummaryRead(
        club_id=seats[0].branch.club_id,
        branch_id=branch_id,
        active_sessions=active_sessions,
        active_reservations=active_reservations,
        occupied_seats=sum(1 for seat in seats if seat.operational_status == SeatOperationalStatus.OCCUPIED.value),
        available_seats=sum(1 for seat in seats if seat.operational_status == SeatOperationalStatus.AVAILABLE.value),
        maintenance_seats=sum(
            1 for seat in seats if seat.operational_status == SeatOperationalStatus.MAINTENANCE.value
        ),
        offline_seats=sum(1 for seat in seats if seat.operational_status == SeatOperationalStatus.OFFLINE.value),
        zone_load=list(zone_map.values()),
    )
