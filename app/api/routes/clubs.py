from fastapi import APIRouter

from app.schemas.club import ClubCreate, ClubRead
from app.services.club import create_club, list_clubs


router = APIRouter()


@router.get("", response_model=list[ClubRead])
def get_clubs() -> list[ClubRead]:
    return list_clubs()


@router.post("", response_model=ClubRead)
def post_club(payload: ClubCreate) -> ClubRead:
    return create_club(payload)
