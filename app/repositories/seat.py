from app.schemas.seat import SeatCreate, SeatRead


def list_items() -> list[SeatRead]:
    return [SeatRead(id=1, zone_id=1, code="A1")]


def create_item(payload: SeatCreate) -> SeatRead:
    return SeatRead(id=2, **payload.model_dump())
