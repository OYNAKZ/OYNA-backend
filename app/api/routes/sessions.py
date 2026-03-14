from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.schemas.session import SessionCreate, SessionRead
from app.services.session import create_session, list_sessions


router = APIRouter()


@router.get("", response_model=list[SessionRead])
def get_sessions(db: Session = Depends(get_db)) -> list[SessionRead]:
    return list_sessions(db)


@router.post("", response_model=SessionRead)
def post_session(payload: SessionCreate, db: Session = Depends(get_db)) -> SessionRead:
    return create_session(db, payload)
