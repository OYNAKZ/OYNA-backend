from fastapi import APIRouter

from app.schemas.session import SessionCreate, SessionRead
from app.services.session import create_session, list_sessions


router = APIRouter()


@router.get("", response_model=list[SessionRead])
def get_sessions() -> list[SessionRead]:
    return list_sessions()


@router.post("", response_model=SessionRead)
def post_session(payload: SessionCreate) -> SessionRead:
    return create_session(payload)
