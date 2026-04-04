from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.constants import ReservationStatus, SeatOperationalStatus, SessionStatus, UserRole
from app.models import Branch, Club, Reservation, Seat, User, Zone
from app.models import Session as SessionModel
from app.repositories.assignment import StaffAssignmentRepository
from app.repositories.user import UserRepository
from app.schemas.assignment import StaffAssignmentCreate, StaffAssignmentRead, StaffAssignmentScopeRead
from app.schemas.operations import ClubZoneLoadRead, OwnerAnalyticsRead, OwnerBranchLoadRead, OwnerClubOverviewRead
from app.services.policies import ensure_can_view_owner_club, owner_club_ids


def _owner_clubs(db: Session, current_user: User) -> list[Club]:
    club_ids = owner_club_ids(db, current_user)
    if current_user.role not in (UserRole.OWNER.value, UserRole.PLATFORM_ADMIN.value):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
    if current_user.role == UserRole.PLATFORM_ADMIN.value:
        return list(db.scalars(select(Club).order_by(Club.id)))
    if not club_ids:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient scope")
    return list(db.scalars(select(Club).where(Club.id.in_(club_ids)).order_by(Club.id)))


def list_owner_clubs(db: Session, current_user: User) -> list[OwnerClubOverviewRead]:
    clubs = _owner_clubs(db, current_user)
    results: list[OwnerClubOverviewRead] = []
    for club in clubs:
        branches = list(db.scalars(select(Branch).where(Branch.club_id == club.id)))
        branch_ids = [branch.id for branch in branches]
        zones = list(db.scalars(select(Zone).where(Zone.branch_id.in_(branch_ids)))) if branch_ids else []
        zone_ids = [zone.id for zone in zones]
        seats = list(db.scalars(select(Seat).where(Seat.zone_id.in_(zone_ids)))) if zone_ids else []
        seat_ids = [seat.id for seat in seats]
        active_sessions = len(
            list(
                db.scalars(
                    select(SessionModel).where(
                        SessionModel.seat_id.in_(seat_ids), SessionModel.status == SessionStatus.ACTIVE.value
                    )
                )
            )
        )
        active_reservations = len(
            list(
                db.scalars(
                    select(Reservation).where(
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
            )
        )
        occupancy_rate = active_sessions / len(seats) if seats else 0.0
        results.append(
            OwnerClubOverviewRead(
                club=club,
                branch_count=len(branches),
                zone_count=len(zones),
                seat_count=len(seats),
                active_sessions=active_sessions,
                active_reservations=active_reservations,
                current_occupancy_rate=occupancy_rate,
            )
        )
    return results


def _resolve_range(
    period: str | None,
    range_start: datetime | None,
    range_end: datetime | None,
) -> tuple[datetime, datetime]:
    now = datetime.now(timezone.utc)
    if period == "today":
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=1)
        return start, end
    if period == "7d":
        return now - timedelta(days=7), now
    if period == "30d":
        return now - timedelta(days=30), now
    if range_start is None or range_end is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Custom range requires start and end",
        )
    return range_start, range_end


def owner_analytics(
    db: Session,
    current_user: User,
    *,
    club_id: int | None,
    period: str | None,
    range_start: datetime | None,
    range_end: datetime | None,
) -> OwnerAnalyticsRead:
    club_ids = owner_club_ids(db, current_user)
    if current_user.role == UserRole.PLATFORM_ADMIN.value:
        club_ids = set(db.scalars(select(Club.id)))
    elif current_user.role != UserRole.OWNER.value:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
    elif not club_ids:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient scope")

    if club_id is not None:
        ensure_can_view_owner_club(db, current_user, club_id)
        club_ids = {club_id}

    start, end = _resolve_range(period, range_start, range_end)

    seats = list(
        db.scalars(
            select(Seat)
            .options(joinedload(Seat.zone).joinedload(Zone.branch))
            .join(Zone)
            .join(Branch)
            .where(Branch.club_id.in_(club_ids))
        ).unique()
    )
    seat_ids = [seat.id for seat in seats]
    total_reservations = len(
        list(
            db.scalars(
                select(Reservation).where(
                    Reservation.seat_id.in_(seat_ids),
                    Reservation.start_at >= start,
                    Reservation.start_at <= end,
                )
            )
        )
    )
    active_reservations = len(
        list(
            db.scalars(
                select(Reservation).where(
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
        )
    )
    cancellations = len(
        list(
            db.scalars(
                select(Reservation).where(
                    Reservation.seat_id.in_(seat_ids),
                    Reservation.status == ReservationStatus.CANCELLED.value,
                    Reservation.updated_at >= start,
                    Reservation.updated_at <= end,
                )
            )
        )
    )
    finished_sessions = len(
        list(
            db.scalars(
                select(SessionModel).where(
                    SessionModel.seat_id.in_(seat_ids),
                    SessionModel.status.in_([SessionStatus.COMPLETED.value, SessionStatus.FINISHED.value]),
                    SessionModel.started_at >= start,
                    SessionModel.started_at <= end,
                )
            )
        )
    )
    active_sessions = len(
        list(
            db.scalars(
                select(SessionModel).where(
                    SessionModel.seat_id.in_(seat_ids),
                    SessionModel.status == SessionStatus.ACTIVE.value,
                )
            )
        )
    )

    branch_load: list[OwnerBranchLoadRead] = []
    zone_load: list[ClubZoneLoadRead] = []
    branch_map: dict[int, list[Seat]] = {}
    zone_map: dict[int, list[Seat]] = {}
    for seat in seats:
        branch_map.setdefault(seat.branch.id, []).append(seat)
        zone_map.setdefault(seat.zone.id, []).append(seat)

    for branch_id, branch_seats in branch_map.items():
        branch_load.append(
            OwnerBranchLoadRead(
                branch=branch_seats[0].branch,
                occupancy_rate=(
                    sum(1 for seat in branch_seats if seat.operational_status == SeatOperationalStatus.OCCUPIED.value)
                    / len(branch_seats)
                ),
            )
        )

    for _, zone_seats in zone_map.items():
        zone = zone_seats[0].zone
        zone_load.append(
            ClubZoneLoadRead(
                zone=zone,
                total_seats=len(zone_seats),
                occupied_seats=sum(
                    1 for seat in zone_seats if seat.operational_status == SeatOperationalStatus.OCCUPIED.value
                ),
                reserved_seats=sum(
                    1 for seat in zone_seats if seat.operational_status == SeatOperationalStatus.RESERVED.value
                ),
                maintenance_seats=sum(
                    1 for seat in zone_seats if seat.operational_status == SeatOperationalStatus.MAINTENANCE.value
                ),
                offline_seats=sum(
                    1 for seat in zone_seats if seat.operational_status == SeatOperationalStatus.OFFLINE.value
                ),
                available_seats=sum(
                    1 for seat in zone_seats if seat.operational_status == SeatOperationalStatus.AVAILABLE.value
                ),
            )
        )

    unavailable = sum(
        1
        for seat in seats
        if seat.operational_status in (SeatOperationalStatus.MAINTENANCE.value, SeatOperationalStatus.OFFLINE.value)
    )
    return OwnerAnalyticsRead(
        club_ids=sorted(club_ids),
        range_start=start,
        range_end=end,
        total_reservations=total_reservations,
        active_reservations=active_reservations,
        cancellations_count=cancellations,
        completed_sessions=finished_sessions,
        active_sessions=active_sessions,
        club_occupancy_rate=(active_sessions / len(seats)) if seats else 0.0,
        branch_load=branch_load,
        zone_load=zone_load,
        unavailable_seat_ratio=(unavailable / len(seats)) if seats else 0.0,
    )


def assign_staff(db: Session, payload: StaffAssignmentCreate, current_user: User) -> StaffAssignmentRead:
    ensure_can_view_owner_club(db, current_user, payload.club_id)
    user = UserRepository(db).get_by_id(payload.user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if user.role != payload.role_in_scope:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User role does not match scope role")
    assignment = StaffAssignmentRepository(db).get_active(
        user_id=payload.user_id,
        club_id=payload.club_id,
        branch_id=payload.branch_id,
        role_in_scope=payload.role_in_scope,
    )
    if assignment is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Assignment already exists")
    return StaffAssignmentRead.model_validate(
        StaffAssignmentRepository(db).create(
            user_id=payload.user_id,
            club_id=payload.club_id,
            branch_id=payload.branch_id,
            role_in_scope=payload.role_in_scope,
        )
    )


def deactivate_staff_assignment(db: Session, assignment_id: int, current_user: User) -> StaffAssignmentRead:
    assignment = StaffAssignmentRepository(db).get_by_id(assignment_id)
    if assignment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found")
    ensure_can_view_owner_club(db, current_user, assignment.club_id)
    return StaffAssignmentRead.model_validate(StaffAssignmentRepository(db).deactivate(assignment))


def list_club_staff(db: Session, club_id: int, current_user: User) -> list[StaffAssignmentRead]:
    ensure_can_view_owner_club(db, current_user, club_id)
    return [StaffAssignmentRead.model_validate(item) for item in StaffAssignmentRepository(db).list_for_club(club_id)]


def get_staff_scope(db: Session, user_id: int, current_user: User) -> StaffAssignmentScopeRead:
    assignments = StaffAssignmentRepository(db).list_active_for_user(user_id)
    visible = []
    for assignment in assignments:
        ensure_can_view_owner_club(db, current_user, assignment.club_id)
        visible.append(StaffAssignmentRead.model_validate(assignment))
    return StaffAssignmentScopeRead(user_id=user_id, assignments=visible)
