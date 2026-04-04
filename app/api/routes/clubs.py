from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, require_roles
from app.core.constants import UserRole
from app.core.db import get_db
from app.models.user import User
from app.schemas.club import ClubCreate, ClubRead
from app.services.club import create_club, list_clubs

router = APIRouter()


@router.get("", response_model=list[ClubRead])
def get_clubs(db: Session = Depends(get_db)) -> list[ClubRead]:
    return list_clubs(db)


@router.post("", response_model=ClubRead)
def post_club(
    payload: ClubCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: object = Depends(require_roles(UserRole.OWNER, UserRole.PLATFORM_ADMIN)),
) -> ClubRead:
    return create_club(db, payload, current_user)
