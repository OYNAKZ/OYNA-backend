from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import require_roles
from app.core.constants import UserRole
from app.core.db import get_db
from app.schemas.seat import SeatAvailabilityRead, SeatCreate, SeatRead
from app.services.seat import create_seat, get_seat_availability, list_seats

router = APIRouter()


@router.get("", response_model=list[SeatRead])
def get_seats(db: Session = Depends(get_db)) -> list[SeatRead]:
    return list_seats(db)


@router.get("/{seat_id}/availability", response_model=SeatAvailabilityRead)
def get_availability(
    seat_id: int,
    date_value: str = Query(..., alias="date"),
    db: Session = Depends(get_db),
) -> SeatAvailabilityRead:
    try:
        target_date = date.fromisoformat(date_value)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid date") from exc
    return get_seat_availability(db, seat_id, target_date)


@router.post("", response_model=SeatRead)
def post_seat(
    payload: SeatCreate,
    db: Session = Depends(get_db),
    _: object = Depends(require_roles(UserRole.CLUB_ADMIN, UserRole.OWNER, UserRole.PLATFORM_ADMIN)),
) -> SeatRead:
    return create_seat(db, payload)
