from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.constants import ScopeRole, UserRole
from app.models import Branch, Reservation, Seat, StaffAssignment, User
from app.models import Session as SessionModel


def _forbidden() -> HTTPException:
    return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient scope")


def ensure_self_or_platform_admin(current_user: User, target_user_id: int) -> None:
    if current_user.role == UserRole.PLATFORM_ADMIN.value:
        return
    if current_user.id == target_user_id:
        return
    raise _forbidden()


def ensure_staff_scope_access(db: Session, user: User) -> None:
    if user.role == UserRole.USER.value:
        raise _forbidden()
    ensure_active_scope_assignment(db, user)


def _active_assignments(db: Session, user_id: int, role_in_scope: str) -> list[StaffAssignment]:
    stmt = select(StaffAssignment).where(
        StaffAssignment.user_id == user_id,
        StaffAssignment.role_in_scope == role_in_scope,
        StaffAssignment.is_active.is_(True),
    )
    return list(db.scalars(stmt))


def owner_club_ids(db: Session, user: User) -> set[int]:
    if user.role == UserRole.PLATFORM_ADMIN.value:
        stmt = select(Branch.club_id).distinct()
        return set(db.scalars(stmt))
    if user.role != UserRole.OWNER.value:
        return set()
    return {assignment.club_id for assignment in _active_assignments(db, user.id, ScopeRole.OWNER.value)}


def admin_scope(db: Session, user: User) -> tuple[set[int], set[int]]:
    if user.role == UserRole.PLATFORM_ADMIN.value:
        branch_ids = set(db.scalars(select(Branch.id)))
        club_ids = set(db.scalars(select(Branch.club_id).distinct()))
        return club_ids, branch_ids
    if user.role != UserRole.CLUB_ADMIN.value:
        return set(), set()

    assignments = _active_assignments(db, user.id, ScopeRole.CLUB_ADMIN.value)
    club_ids = {assignment.club_id for assignment in assignments}
    branch_ids = {assignment.branch_id for assignment in assignments if assignment.branch_id is not None}
    if not assignments and user.club_id is not None:
        club_ids.add(user.club_id)
    return club_ids, branch_ids


def can_manage_club(db: Session, user: User, club_id: int) -> bool:
    if user.role == UserRole.PLATFORM_ADMIN.value:
        return True
    if user.role == UserRole.OWNER.value:
        return club_id in owner_club_ids(db, user)
    club_ids, _ = admin_scope(db, user)
    return club_id in club_ids


def can_manage_branch(db: Session, user: User, branch_id: int) -> bool:
    if user.role == UserRole.PLATFORM_ADMIN.value:
        return True

    branch = db.get(Branch, branch_id)
    if branch is None:
        return False

    if user.role == UserRole.OWNER.value:
        return branch.club_id in owner_club_ids(db, user)

    club_ids, branch_ids = admin_scope(db, user)
    return branch.club_id in club_ids and (not branch_ids or branch.id in branch_ids)


def reservation_scope_clause(db: Session, user: User) -> tuple[set[int], set[int], bool]:
    if user.role == UserRole.PLATFORM_ADMIN.value:
        return set(), set(), True
    if user.role == UserRole.OWNER.value:
        return owner_club_ids(db, user), set(), False
    if user.role == UserRole.CLUB_ADMIN.value:
        club_ids, branch_ids = admin_scope(db, user)
        return club_ids, branch_ids, False
    return set(), set(), False


def ensure_can_view_owner_club(db: Session, user: User, club_id: int) -> None:
    if not can_manage_club(db, user, club_id) or user.role not in (UserRole.OWNER.value, UserRole.PLATFORM_ADMIN.value):
        raise _forbidden()


def ensure_can_manage_club(db: Session, user: User, club_id: int) -> None:
    if not can_manage_club(db, user, club_id):
        raise _forbidden()


def ensure_can_manage_branch(db: Session, user: User, branch_id: int) -> None:
    if not can_manage_branch(db, user, branch_id):
        raise _forbidden()


def ensure_can_operate_reservation(db: Session, user: User, reservation: Reservation) -> None:
    branch = reservation.seat.branch if reservation.seat is not None else None
    if branch is None:
        raise _forbidden()
    if not can_manage_branch(db, user, branch.id):
        raise _forbidden()


def ensure_can_operate_session(db: Session, user: User, session: SessionModel) -> None:
    seat = session.seat
    branch = seat.branch if seat is not None else None
    if branch is None:
        raise _forbidden()
    if not can_manage_branch(db, user, branch.id):
        raise _forbidden()


def ensure_can_operate_seat(db: Session, user: User, seat: Seat) -> None:
    branch = seat.branch
    if branch is None or not can_manage_branch(db, user, branch.id):
        raise _forbidden()


def ensure_active_scope_assignment(db: Session, user: User) -> None:
    if user.role == UserRole.PLATFORM_ADMIN.value:
        return
    if user.role == UserRole.OWNER.value and owner_club_ids(db, user):
        return
    if user.role == UserRole.CLUB_ADMIN.value and admin_scope(db, user)[0]:
        return
    raise _forbidden()
