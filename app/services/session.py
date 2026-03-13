from app.repositories import session as repository
from app.schemas.session import SessionCreate, SessionRead


def list_sessions() -> list[SessionRead]:
    return repository.list_items()


def create_session(payload: SessionCreate) -> SessionRead:
    return repository.create_item(payload)
