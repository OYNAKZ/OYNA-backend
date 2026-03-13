from app.schemas.reservation import ReservationCreate, ReservationRead


def list_items() -> list[ReservationRead]:
    return [ReservationRead(id=1, seat_id=1, user_id=1, status="pending")]


def create_item(payload: ReservationCreate) -> ReservationRead:
    return ReservationRead(id=2, **payload.model_dump())
