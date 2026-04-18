from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, require_roles
from app.core.constants import UserRole
from app.core.db import get_db
from app.models.user import User
from app.schemas.session import SessionCreate, SessionRead
from app.services.session import create_session, list_sessions

router = APIRouter()


@router.get("", response_model=list[SessionRead])
def get_sessions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[SessionRead]:
    return list_sessions(db, current_user)


@router.post("", response_model=SessionRead)
def post_session(
    payload: SessionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: object = Depends(require_roles(UserRole.CLUB_ADMIN, UserRole.OWNER, UserRole.PLATFORM_ADMIN)),
) -> SessionRead:
    return create_session(db, payload, current_user)
