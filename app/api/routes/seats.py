from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.schemas.seat import SeatCreate, SeatRead
from app.services.seat import create_seat, list_seats


router = APIRouter()


@router.get("", response_model=list[SeatRead])
def get_seats(db: Session = Depends(get_db)) -> list[SeatRead]:
    return list_seats(db)


@router.post("", response_model=SeatRead)
def post_seat(payload: SeatCreate, db: Session = Depends(get_db)) -> SeatRead:
    return create_seat(db, payload)
