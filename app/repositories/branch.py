from app.schemas.branch import BranchCreate, BranchRead


def list_items() -> list[BranchRead]:
    return [BranchRead(id=1, club_id=1, name="Main Branch")]


def create_item(payload: BranchCreate) -> BranchRead:
    return BranchRead(id=2, **payload.model_dump())
