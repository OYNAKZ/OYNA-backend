from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.branch import Branch
from app.models.user import User
from app.repositories import zone as repository
from app.schemas.zone import ZoneCreate, ZoneRead
from app.services.policies import ensure_can_manage_branch, ensure_staff_scope_access


def list_zones(db: Session) -> list[ZoneRead]:
    return repository.list_items(db)


def create_zone(db: Session, payload: ZoneCreate, current_user: User) -> ZoneRead:
    branch = db.get(Branch, payload.branch_id)
    if branch is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Branch not found")
    ensure_staff_scope_access(db, current_user)
    ensure_can_manage_branch(db, current_user, branch.id)
    try:
        return repository.create_item(db, payload)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Zone already exists") from exc
