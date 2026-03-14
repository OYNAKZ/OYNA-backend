from sqlalchemy.orm import Session

from app.repositories import session as repository
from app.schemas.session import SessionCreate, SessionRead


def list_sessions(db: Session) -> list[SessionRead]:
    return repository.list_items(db)


def create_session(db: Session, payload: SessionCreate) -> SessionRead:
    return repository.create_item(db, payload)
