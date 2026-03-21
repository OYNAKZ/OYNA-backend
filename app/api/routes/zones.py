from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies import require_roles
from app.core.constants import UserRole
from app.core.db import get_db
from app.schemas.zone import ZoneCreate, ZoneRead
from app.services.zone import create_zone, list_zones

router = APIRouter()


@router.get("", response_model=list[ZoneRead])
def get_zones(db: Session = Depends(get_db)) -> list[ZoneRead]:
    return list_zones(db)


@router.post("", response_model=ZoneRead)
def post_zone(
    payload: ZoneCreate,
    db: Session = Depends(get_db),
    _: object = Depends(require_roles(UserRole.CLUB_ADMIN, UserRole.OWNER, UserRole.PLATFORM_ADMIN)),
) -> ZoneRead:
    return create_zone(db, payload)
