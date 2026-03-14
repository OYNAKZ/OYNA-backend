from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.branch import Branch
from app.schemas.branch import BranchCreate, BranchUpdate


class BranchRepository:
    def __init__(self, db: Session):
        self.db = db

    def list(self) -> list[Branch]:
        return list(self.db.scalars(select(Branch).order_by(Branch.id)))

    def get_by_id(self, branch_id: int) -> Branch | None:
        return self.db.get(Branch, branch_id)

    def list_by_club(self, club_id: int) -> list[Branch]:
        stmt = select(Branch).where(Branch.club_id == club_id).order_by(Branch.id)
        return list(self.db.scalars(stmt))

    def create(self, payload: BranchCreate) -> Branch:
        item = Branch(**payload.model_dump())
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    def update(self, branch: Branch, payload: BranchUpdate) -> Branch:
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(branch, field, value)
        self.db.add(branch)
        self.db.commit()
        self.db.refresh(branch)
        return branch


def list_items(db: Session) -> list[Branch]:
    return BranchRepository(db).list()


def create_item(db: Session, payload: BranchCreate) -> Branch:
    return BranchRepository(db).create(payload)
