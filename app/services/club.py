from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.repositories import club as repository
from app.schemas.club import ClubCreate, ClubRead


def list_clubs(db: Session) -> list[ClubRead]:
    return repository.list_items(db)


def create_club(db: Session, payload: ClubCreate) -> ClubRead:
    try:
        return repository.create_item(db, payload)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Club already exists") from exc
