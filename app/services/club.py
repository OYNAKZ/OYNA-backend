from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.constants import ScopeRole, UserRole
from app.models.user import User
from app.repositories import club as repository
from app.repositories.assignment import StaffAssignmentRepository
from app.schemas.club import ClubCreate, ClubRead


def list_clubs(db: Session) -> list[ClubRead]:
    return repository.list_items(db)


def create_club(db: Session, payload: ClubCreate, current_user: User) -> ClubRead:
    try:
        club = repository.create_item(db, payload)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Club already exists") from exc
    if current_user.role == UserRole.OWNER.value:
        StaffAssignmentRepository(db).create(
            user_id=current_user.id,
            club_id=club.id,
            branch_id=None,
            role_in_scope=ScopeRole.OWNER.value,
        )
    return club
