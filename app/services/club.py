from app.repositories import club as repository
from app.schemas.club import ClubCreate, ClubRead


def list_clubs() -> list[ClubRead]:
    return repository.list_items()


def create_club(payload: ClubCreate) -> ClubRead:
    return repository.create_item(payload)
