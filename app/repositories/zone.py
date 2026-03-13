from app.schemas.zone import ZoneCreate, ZoneRead


def list_items() -> list[ZoneRead]:
    return [ZoneRead(id=1, branch_id=1, name="VIP")]


def create_item(payload: ZoneCreate) -> ZoneRead:
    return ZoneRead(id=2, **payload.model_dump())
