from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, require_roles
from app.core.constants import UserRole
from app.core.db import get_db
from app.models.user import User
from app.schemas.branch import BranchCreate, BranchRead
from app.services.branch import create_branch, list_branches

router = APIRouter()


@router.get("", response_model=list[BranchRead])
def get_branches(db: Session = Depends(get_db)) -> list[BranchRead]:
    return list_branches(db)


@router.post("", response_model=BranchRead)
def post_branch(
    payload: BranchCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: object = Depends(require_roles(UserRole.CLUB_ADMIN, UserRole.OWNER, UserRole.PLATFORM_ADMIN)),
) -> BranchRead:
    return create_branch(db, payload, current_user)
