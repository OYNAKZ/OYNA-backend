from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.zone import Zone
from app.schemas.zone import ZoneCreate, ZoneRead


def list_items(db: Session) -> list[Zone]:
    return list(db.scalars(select(Zone).order_by(Zone.id)))


def create_item(db: Session, payload: ZoneCreate) -> Zone:
    item = Zone(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item
