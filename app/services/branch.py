from app.repositories import branch as repository
from app.schemas.branch import BranchCreate, BranchRead


def list_branches() -> list[BranchRead]:
    return repository.list_items()


def create_branch(payload: BranchCreate) -> BranchRead:
    return repository.create_item(payload)
