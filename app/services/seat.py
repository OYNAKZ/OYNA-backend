from app.repositories import seat as repository
from app.schemas.seat import SeatCreate, SeatRead


def list_seats() -> list[SeatRead]:
    return repository.list_items()


def create_seat(payload: SeatCreate) -> SeatRead:
    return repository.create_item(payload)
