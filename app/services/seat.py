from datetime import date, datetime, time, timezone

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.zone import Zone
from app.repositories.reservation import ReservationRepository
from app.repositories.session import SessionRepository
from app.repositories import seat as repository
from app.schemas.seat import SeatAvailabilityRead, SeatAvailabilitySlot, SeatCreate, SeatRead


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def list_seats(db: Session) -> list[SeatRead]:
    return repository.list_items(db)


def create_seat(db: Session, payload: SeatCreate) -> SeatRead:
    if db.get(Zone, payload.zone_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Zone not found")
    try:
        return repository.create_item(db, payload)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Seat code already exists in this zone",
        ) from exc


def get_seat_availability(db: Session, seat_id: int, target_date: date) -> SeatAvailabilityRead:
    seat = repository.SeatRepository(db).get_by_id(seat_id)
    if seat is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Seat not found")

    day_start = datetime.combine(target_date, time.min, tzinfo=timezone.utc)
    day_end = datetime.combine(target_date, time.max, tzinfo=timezone.utc)

    intervals = ReservationRepository(db).list_booked_intervals_for_day(seat_id=seat_id, target_date=target_date)
    intervals.extend(SessionRepository(db).list_booked_intervals_for_day(seat_id=seat_id, target_date=target_date))

    clamped = []
    for start_at, end_at in intervals:
        start = max(_as_utc(start_at), day_start)
        end = min(_as_utc(end_at), day_end)
        if start < end:
            clamped.append((start, end))

    merged: list[tuple[datetime, datetime]] = []
    for start_at, end_at in sorted(clamped, key=lambda item: item[0]):
        if not merged or start_at > merged[-1][1]:
            merged.append((start_at, end_at))
            continue
        merged[-1] = (merged[-1][0], max(merged[-1][1], end_at))

    slots: list[SeatAvailabilitySlot] = []
    cursor = day_start
    for start_at, end_at in merged:
        if cursor < start_at:
            slots.append(SeatAvailabilitySlot(start=cursor, end=start_at, status="free"))
        slots.append(SeatAvailabilitySlot(start=start_at, end=end_at, status="booked"))
        cursor = max(cursor, end_at)

    if cursor < day_end:
        slots.append(SeatAvailabilitySlot(start=cursor, end=day_end, status="free"))

    if not slots:
        slots.append(SeatAvailabilitySlot(start=day_start, end=day_end, status="free"))

    return SeatAvailabilityRead(seat_id=seat_id, date=target_date.isoformat(), slots=slots)
