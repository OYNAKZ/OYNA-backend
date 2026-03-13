from fastapi import APIRouter

from app.schemas.reservation import ReservationCreate, ReservationRead
from app.services.reservation import create_reservation, list_reservations


router = APIRouter()


@router.get("", response_model=list[ReservationRead])
def get_reservations() -> list[ReservationRead]:
    return list_reservations()


@router.post("", response_model=ReservationRead)
def post_reservation(payload: ReservationCreate) -> ReservationRead:
    return create_reservation(payload)
