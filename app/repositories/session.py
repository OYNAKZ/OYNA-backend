from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.session import Session as SessionModel
from app.core.constants import SessionStatus
from app.schemas.session import SessionCreate


class SessionRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, session_id: int) -> SessionModel | None:
        return self.db.get(SessionModel, session_id)

    def list_active(self) -> list[SessionModel]:
        stmt = select(SessionModel).where(SessionModel.status == SessionStatus.ACTIVE.value).order_by(SessionModel.id)
        return list(self.db.scalars(stmt))

    def create(self, payload: SessionCreate) -> SessionModel:
        item = SessionModel(**payload.model_dump())
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    def update(self, session: SessionModel, **changes) -> SessionModel:
        for field, value in changes.items():
            setattr(session, field, value)
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        return session


def list_items(db: Session) -> list[SessionModel]:
    return list(db.scalars(select(SessionModel).order_by(SessionModel.id)))


def create_item(db: Session, payload: SessionCreate) -> SessionModel:
    return SessionRepository(db).create(payload)
