from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.club import Club
from app.repositories import branch as repository
from app.schemas.branch import BranchCreate, BranchRead


def list_branches(db: Session) -> list[BranchRead]:
    return repository.list_items(db)


def create_branch(db: Session, payload: BranchCreate) -> BranchRead:
    if db.get(Club, payload.club_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Club not found")
    try:
        return repository.create_item(db, payload)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Branch already exists") from exc
