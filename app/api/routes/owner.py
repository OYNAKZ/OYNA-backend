from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, require_roles
from app.core.constants import UserRole
from app.core.db import get_db
from app.models.user import User
from app.schemas.assignment import StaffAssignmentCreate, StaffAssignmentRead, StaffAssignmentScopeRead
from app.schemas.operations import OwnerAnalyticsRead, OwnerClubOverviewRead
from app.services.owner import (
    assign_staff,
    deactivate_staff_assignment,
    get_staff_scope,
    list_club_staff,
    list_owner_clubs,
    owner_analytics,
)

router = APIRouter(
    prefix="/owner",
    tags=["owner"],
    dependencies=[Depends(require_roles(UserRole.OWNER, UserRole.PLATFORM_ADMIN))],
)


@router.get("/clubs", response_model=list[OwnerClubOverviewRead])
def get_owner_clubs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[OwnerClubOverviewRead]:
    return list_owner_clubs(db, current_user)


@router.get("/analytics", response_model=OwnerAnalyticsRead)
def get_owner_analytics(
    club_id: int | None = None,
    period: str | None = Query("7d"),
    range_start: datetime | None = Query(None, alias="from"),
    range_end: datetime | None = Query(None, alias="to"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> OwnerAnalyticsRead:
    return owner_analytics(
        db,
        current_user,
        club_id=club_id,
        period=period,
        range_start=range_start,
        range_end=range_end,
    )


@router.get("/clubs/{club_id}/staff", response_model=list[StaffAssignmentRead])
def get_club_staff(
    club_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[StaffAssignmentRead]:
    return list_club_staff(db, club_id, current_user)


@router.post("/staff-assignments", response_model=StaffAssignmentRead)
def post_staff_assignment(
    payload: StaffAssignmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StaffAssignmentRead:
    return assign_staff(db, payload, current_user)


@router.patch("/staff-assignments/{assignment_id}/deactivate", response_model=StaffAssignmentRead)
def patch_staff_assignment(
    assignment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StaffAssignmentRead:
    return deactivate_staff_assignment(db, assignment_id, current_user)


@router.get("/staff/{user_id}/scope", response_model=StaffAssignmentScopeRead)
def get_user_scope(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StaffAssignmentScopeRead:
    return get_staff_scope(db, user_id, current_user)
