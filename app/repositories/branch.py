from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.branch import Branch
from app.schemas.branch import BranchCreate, BranchRead


def list_items(db: Session) -> list[Branch]:
    return list(db.scalars(select(Branch).order_by(Branch.id)))


def create_item(db: Session, payload: BranchCreate) -> Branch:
    item = Branch(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item
