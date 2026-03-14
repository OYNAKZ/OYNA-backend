from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.session import Session as SessionModel
from app.schemas.session import SessionCreate, SessionRead


def list_items(db: Session) -> list[SessionModel]:
    return list(db.scalars(select(SessionModel).order_by(SessionModel.id)))


def create_item(db: Session, payload: SessionCreate) -> SessionModel:
    item = SessionModel(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item
