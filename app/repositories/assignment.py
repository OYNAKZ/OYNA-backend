from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.staff_assignment import StaffAssignment


class StaffAssignmentRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_active_for_user(self, user_id: int) -> list[StaffAssignment]:
        stmt = select(StaffAssignment).where(StaffAssignment.user_id == user_id, StaffAssignment.is_active.is_(True))
        return list(self.db.scalars(stmt))

    def list_for_club(self, club_id: int) -> list[StaffAssignment]:
        stmt = select(StaffAssignment).where(StaffAssignment.club_id == club_id, StaffAssignment.is_active.is_(True))
        return list(self.db.scalars(stmt))

    def get_by_id(self, assignment_id: int) -> StaffAssignment | None:
        return self.db.get(StaffAssignment, assignment_id)

    def get_active(
        self,
        *,
        user_id: int,
        club_id: int,
        branch_id: int | None,
        role_in_scope: str,
    ) -> StaffAssignment | None:
        stmt = select(StaffAssignment).where(
            StaffAssignment.user_id == user_id,
            StaffAssignment.club_id == club_id,
            StaffAssignment.role_in_scope == role_in_scope,
            StaffAssignment.is_active.is_(True),
        )
        if branch_id is None:
            stmt = stmt.where(StaffAssignment.branch_id.is_(None))
        else:
            stmt = stmt.where(StaffAssignment.branch_id == branch_id)
        return self.db.scalar(stmt)

    def create(self, *, user_id: int, club_id: int, branch_id: int | None, role_in_scope: str) -> StaffAssignment:
        item = StaffAssignment(
            user_id=user_id,
            club_id=club_id,
            branch_id=branch_id,
            role_in_scope=role_in_scope,
            is_active=True,
        )
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    def deactivate(self, assignment: StaffAssignment) -> StaffAssignment:
        assignment.is_active = False
        self.db.add(assignment)
        self.db.commit()
        self.db.refresh(assignment)
        return assignment
