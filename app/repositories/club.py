from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.club import Club
from app.schemas.club import ClubCreate, ClubRead


def list_items(db: Session) -> list[Club]:
    return list(db.scalars(select(Club).order_by(Club.id)))


def create_item(db: Session, payload: ClubCreate) -> Club:
    item = Club(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item
