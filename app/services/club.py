from sqlalchemy.orm import Session

from app.repositories import club as repository
from app.schemas.club import ClubCreate, ClubRead


def list_clubs(db: Session) -> list[ClubRead]:
    return repository.list_items(db)


def create_club(db: Session, payload: ClubCreate) -> ClubRead:
    return repository.create_item(db, payload)
