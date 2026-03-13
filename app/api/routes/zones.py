from fastapi import APIRouter

from app.schemas.zone import ZoneCreate, ZoneRead
from app.services.zone import create_zone, list_zones


router = APIRouter()


@router.get("", response_model=list[ZoneRead])
def get_zones() -> list[ZoneRead]:
    return list_zones()


@router.post("", response_model=ZoneRead)
def post_zone(payload: ZoneCreate) -> ZoneRead:
    return create_zone(payload)
