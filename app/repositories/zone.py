from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.zone import Zone
from app.schemas.zone import ZoneCreate, ZoneUpdate


class ZoneRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_by_branch(self, branch_id: int) -> list[Zone]:
        stmt = select(Zone).where(Zone.branch_id == branch_id).order_by(Zone.id)
        return list(self.db.scalars(stmt))

    def get_by_id(self, zone_id: int) -> Zone | None:
        return self.db.get(Zone, zone_id)

    def create(self, payload: ZoneCreate) -> Zone:
        item = Zone(**payload.model_dump())
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    def update(self, zone: Zone, payload: ZoneUpdate) -> Zone:
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(zone, field, value)
        self.db.add(zone)
        self.db.commit()
        self.db.refresh(zone)
        return zone


def list_items(db: Session) -> list[Zone]:
    stmt = select(Zone).order_by(Zone.id)
    return list(db.scalars(stmt))


def create_item(db: Session, payload: ZoneCreate) -> Zone:
    return ZoneRepository(db).create(payload)
