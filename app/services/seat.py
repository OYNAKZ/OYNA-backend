from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.zone import Zone
from app.repositories import seat as repository
from app.schemas.seat import SeatCreate, SeatRead


def list_seats(db: Session) -> list[SeatRead]:
    return repository.list_items(db)


def create_seat(db: Session, payload: SeatCreate) -> SeatRead:
    if db.get(Zone, payload.zone_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Zone not found")
    try:
        return repository.create_item(db, payload)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Seat code already exists in this zone",
        ) from exc
