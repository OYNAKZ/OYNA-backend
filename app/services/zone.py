from app.repositories import zone as repository
from app.schemas.zone import ZoneCreate, ZoneRead


def list_zones() -> list[ZoneRead]:
    return repository.list_items()


def create_zone(payload: ZoneCreate) -> ZoneRead:
    return repository.create_item(payload)
