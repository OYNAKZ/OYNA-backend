from app.schemas.club import ClubCreate, ClubRead


def list_items() -> list[ClubRead]:
    return [ClubRead(id=1, name="Demo Club")]


def create_item(payload: ClubCreate) -> ClubRead:
    return ClubRead(id=2, **payload.model_dump())
