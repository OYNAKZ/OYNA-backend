from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.db import get_db
from app.models.user import User
from app.schemas.reservation import ReservationCreate, ReservationRead
from app.services.reservation import create_reservation, list_reservations

router = APIRouter()


@router.get("", response_model=list[ReservationRead])
def get_reservations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ReservationRead]:
    return list_reservations(db, current_user)


@router.post("", response_model=ReservationRead)
def post_reservation(
    payload: ReservationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ReservationRead:
    return create_reservation(db, payload, current_user)
