from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.db import get_db
from app.models.user import User
from app.schemas.reservation import ReservationCreate, ReservationDetailRead, ReservationRead
from app.services.reservation import cancel_reservation, create_reservation, get_reservation_detail, list_reservations

router = APIRouter()


@router.get("", response_model=list[ReservationRead])
def get_reservations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ReservationRead]:
    return list_reservations(db, current_user)


@router.get("/{reservation_id}", response_model=ReservationDetailRead)
def get_reservation(
    reservation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ReservationDetailRead:
    return get_reservation_detail(db, reservation_id, current_user)


@router.post("", response_model=ReservationRead)
def post_reservation(
    payload: ReservationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ReservationRead:
    return create_reservation(db, payload, current_user)


@router.patch("/{reservation_id}/cancel", response_model=ReservationRead)
def patch_reservation_cancel(
    reservation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ReservationRead:
    return cancel_reservation(db, reservation_id, current_user)
