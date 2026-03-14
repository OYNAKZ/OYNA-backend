from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.club import Club
from app.schemas.club import ClubCreate, ClubUpdate


class ClubRepository:
    def __init__(self, db: Session):
        self.db = db

    def list(self) -> list[Club]:
        return list(self.db.scalars(select(Club).order_by(Club.id)))

    def get_by_id(self, club_id: int) -> Club | None:
        return self.db.get(Club, club_id)

    def create(self, payload: ClubCreate) -> Club:
        item = Club(**payload.model_dump())
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    def update(self, club: Club, payload: ClubUpdate) -> Club:
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(club, field, value)
        self.db.add(club)
        self.db.commit()
        self.db.refresh(club)
        return club


def list_items(db: Session) -> list[Club]:
    return ClubRepository(db).list()


def create_item(db: Session, payload: ClubCreate) -> Club:
    return ClubRepository(db).create(payload)
