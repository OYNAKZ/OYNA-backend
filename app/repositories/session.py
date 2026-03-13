from app.schemas.session import SessionCreate, SessionRead


def list_items() -> list[SessionRead]:
    return [SessionRead(id=1, reservation_id=1, started_at="2026-03-14T00:00:00Z", ended_at=None)]


def create_item(payload: SessionCreate) -> SessionRead:
    return SessionRead(id=2, **payload.model_dump())
