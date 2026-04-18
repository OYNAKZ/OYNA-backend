from datetime import date

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.constants import SeatOperationalStatus
from app.models.user import User
from app.models.zone import Zone
from app.repositories import seat as repository
from app.schemas.seat import SeatAvailabilityRead, SeatAvailabilitySlot, SeatCreate, SeatRead
from app.services.availability import build_daily_availability_slots
from app.services.policies import ensure_can_manage_branch, ensure_staff_scope_access


def list_seats(db: Session) -> list[SeatRead]:
    return repository.list_items(db)


def create_seat(db: Session, payload: SeatCreate, current_user: User) -> SeatRead:
    zone = db.get(Zone, payload.zone_id)
    if zone is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Zone not found")
    ensure_staff_scope_access(db, current_user)
    ensure_can_manage_branch(db, current_user, zone.branch_id)
    try:
        seat = repository.create_item(db, payload)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Seat code already exists in this zone",
        ) from exc
    seat.operational_status = (
        SeatOperationalStatus.MAINTENANCE.value if seat.is_maintenance else SeatOperationalStatus.AVAILABLE.value
    )
    db.add(seat)
    db.commit()
    db.refresh(seat)
    return seat


def get_seat_availability(db: Session, seat_id: int, target_date: date) -> SeatAvailabilityRead:
    seat = repository.SeatRepository(db).get_by_id_with_location(seat_id)
    if seat is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Seat not found")
    slots = [
        SeatAvailabilitySlot(start=start_at, end=end_at, status=status_value)
        for start_at, end_at, status_value in build_daily_availability_slots(db, seat=seat, target_date=target_date)
    ]
    return SeatAvailabilityRead(seat_id=seat_id, date=target_date.isoformat(), slots=slots)
