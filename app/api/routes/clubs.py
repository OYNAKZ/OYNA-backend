from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.schemas.club import ClubCreate, ClubRead
from app.services.club import create_club, list_clubs


router = APIRouter()


@router.get("", response_model=list[ClubRead])
def get_clubs(db: Session = Depends(get_db)) -> list[ClubRead]:
    return list_clubs(db)


@router.post("", response_model=ClubRead)
def post_club(payload: ClubCreate, db: Session = Depends(get_db)) -> ClubRead:
    return create_club(db, payload)
