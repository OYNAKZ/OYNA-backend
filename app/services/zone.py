from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.branch import Branch
from app.repositories import zone as repository
from app.schemas.zone import ZoneCreate, ZoneRead


def list_zones(db: Session) -> list[ZoneRead]:
    return repository.list_items(db)


def create_zone(db: Session, payload: ZoneCreate) -> ZoneRead:
    if db.get(Branch, payload.branch_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Branch not found")
    try:
        return repository.create_item(db, payload)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Zone already exists") from exc
