from app.repositories import reservation as repository
from app.schemas.reservation import ReservationCreate, ReservationRead


def list_reservations() -> list[ReservationRead]:
    return repository.list_items()


def create_reservation(payload: ReservationCreate) -> ReservationRead:
    return repository.create_item(payload)
