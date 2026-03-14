from sqlalchemy.orm import Session

from app.repositories import branch as repository
from app.schemas.branch import BranchCreate, BranchRead


def list_branches(db: Session) -> list[BranchRead]:
    return repository.list_items(db)


def create_branch(db: Session, payload: BranchCreate) -> BranchRead:
    return repository.create_item(db, payload)
