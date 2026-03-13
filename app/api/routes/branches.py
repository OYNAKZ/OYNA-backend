from fastapi import APIRouter

from app.schemas.branch import BranchCreate, BranchRead
from app.services.branch import create_branch, list_branches


router = APIRouter()


@router.get("", response_model=list[BranchRead])
def get_branches() -> list[BranchRead]:
    return list_branches()


@router.post("", response_model=BranchRead)
def post_branch(payload: BranchCreate) -> BranchRead:
    return create_branch(payload)
