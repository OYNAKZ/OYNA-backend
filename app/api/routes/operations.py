from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, require_roles
from app.core.constants import UserRole
from app.core.db import get_db
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.operations import (
    ClubOperationsSummaryRead,
    ReservationOperationsRead,
    SessionOperationsRead,
)
from app.schemas.seat import SeatStatusHistoryRead, SeatStatusUpdate
from app.services.operations import (
    check_in_reservation,
    finish_session,
    get_live_club_summary,
    get_seat_status_history,
    list_operational_reservations,
    list_operational_sessions,
    start_session_from_reservation,
    update_seat_operational_status,
)

router = APIRouter(
    prefix="/operations",
    tags=["operations"],
    dependencies=[Depends(require_roles(UserRole.CLUB_ADMIN, UserRole.OWNER, UserRole.PLATFORM_ADMIN))],
)


@router.get("/reservations", response_model=PaginatedResponse[ReservationOperationsRead])
def get_operational_reservations(
    branch_id: int | None = None,
    zone_id: int | None = None,
    seat_id: int | None = None,
    status_value: str | None = Query(None, alias="status"),
    range_start: datetime | None = Query(None, alias="from"),
    range_end: datetime | None = Query(None, alias="to"),
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PaginatedResponse[ReservationOperationsRead]:
    return list_operational_reservations(
        db,
        current_user,
        branch_id=branch_id,
        zone_id=zone_id,
        seat_id=seat_id,
        status_value=status_value,
        range_start=range_start,
        range_end=range_end,
        page=page,
        page_size=page_size,
    )


@router.get("/sessions", response_model=PaginatedResponse[SessionOperationsRead])
def get_operational_sessions(
    active_only: bool = True,
    branch_id: int | None = None,
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PaginatedResponse[SessionOperationsRead]:
    return list_operational_sessions(
        db,
        current_user,
        active_only=active_only,
        branch_id=branch_id,
        page=page,
        page_size=page_size,
    )


@router.patch("/reservations/{reservation_id}/check-in", response_model=ReservationOperationsRead)
def patch_check_in(
    reservation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ReservationOperationsRead:
    return check_in_reservation(db, reservation_id, current_user)


@router.post("/reservations/{reservation_id}/start-session", response_model=SessionOperationsRead)
def post_start_session(
    reservation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SessionOperationsRead:
    return start_session_from_reservation(db, reservation_id, current_user)


@router.patch("/sessions/{session_id}/finish", response_model=SessionOperationsRead)
def patch_finish_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SessionOperationsRead:
    return finish_session(db, session_id, current_user)


@router.patch("/seats/{seat_id}/status", response_model=SeatStatusHistoryRead)
def patch_seat_status(
    seat_id: int,
    payload: SeatStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SeatStatusHistoryRead:
    return update_seat_operational_status(
        db,
        seat_id,
        new_status=payload.operational_status,
        reason=payload.reason,
        current_user=current_user,
    )


@router.get("/seats/{seat_id}/status-history", response_model=list[SeatStatusHistoryRead])
def get_status_history(
    seat_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[SeatStatusHistoryRead]:
    return get_seat_status_history(db, seat_id, current_user)


@router.get("/summary", response_model=ClubOperationsSummaryRead)
def get_summary(
    branch_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ClubOperationsSummaryRead:
    return get_live_club_summary(db, current_user, branch_id)
