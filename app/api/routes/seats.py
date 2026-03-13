from fastapi import APIRouter

from app.schemas.seat import SeatCreate, SeatRead
from app.services.seat import create_seat, list_seats


router = APIRouter()


@router.get("", response_model=list[SeatRead])
def get_seats() -> list[SeatRead]:
    return list_seats()


@router.post("", response_model=SeatRead)
def post_seat(payload: SeatCreate) -> SeatRead:
    return create_seat(payload)
