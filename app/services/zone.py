from sqlalchemy.orm import Session

from app.repositories import zone as repository
from app.schemas.zone import ZoneCreate, ZoneRead


def list_zones(db: Session) -> list[ZoneRead]:
    return repository.list_items(db)


def create_zone(db: Session, payload: ZoneCreate) -> ZoneRead:
    return repository.create_item(db, payload)
