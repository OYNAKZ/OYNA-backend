from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.constants import ReservationStatus, SeatOperationalStatus
from app.models.seat import Seat
from app.repositories.reservation import ReservationRepository
from app.repositories.seat import SeatRepository
from app.repositories.session import SessionRepository
from app.services.lifecycle import sync_seat_operational_status


BLOCKED_OPERATIONAL_STATUSES = {
    SeatOperationalStatus.MAINTENANCE.value,
    SeatOperationalStatus.OFFLINE.value,
}


@dataclass(slots=True)
class SeatAvailabilityResult:
    seat: Seat | None
    is_available: bool
    reason: str | None = None
    blocked_intervals: list[tuple[datetime, datetime]] | None = None


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def normalize_interval(start_at: datetime, end_at: datetime) -> tuple[datetime, datetime]:
    start = _as_utc(start_at)
    end = _as_utc(end_at)
    if start >= end:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="end_at must be after start_at")
    return start, end


def _seat_state_block_reason(seat: Seat) -> str | None:
    if not seat.is_active:
        return "Seat is inactive"
    if seat.is_maintenance:
        return "Seat is under maintenance"
    if seat.operational_status in BLOCKED_OPERATIONAL_STATUSES:
        return "Seat is not available for reservation"
    return None


def _merge_intervals(intervals: list[tuple[datetime, datetime]]) -> list[tuple[datetime, datetime]]:
    merged: list[tuple[datetime, datetime]] = []
    for start_at, end_at in sorted(intervals, key=lambda item: item[0]):
        if not merged or start_at >= merged[-1][1]:
            merged.append((start_at, end_at))
            continue
        merged[-1] = (merged[-1][0], max(merged[-1][1], end_at))
    return merged


def list_blocked_intervals(
    db: Session,
    *,
    seat_ids: list[int],
    start_at: datetime,
    end_at: datetime,
) -> dict[int, list[tuple[datetime, datetime]]]:
    start, end = normalize_interval(start_at, end_at)
    cleanup_expired_holds(db, now=datetime.now(timezone.utc))
    blocked: dict[int, list[tuple[datetime, datetime]]] = {seat_id: [] for seat_id in seat_ids}

    reservation_rows = ReservationRepository(db).list_overlapping_intervals(
        seat_ids=seat_ids,
        start_at=start,
        end_at=end,
        reference_time=datetime.now(timezone.utc),
    )
    session_rows = SessionRepository(db).list_overlapping_intervals(seat_ids=seat_ids, start_at=start, end_at=end)

    for seat_id, interval_start, interval_end in reservation_rows:
        blocked.setdefault(seat_id, []).append((_as_utc(interval_start), _as_utc(interval_end)))
    for seat_id, interval_start, interval_end in session_rows:
        blocked.setdefault(seat_id, []).append((_as_utc(interval_start), _as_utc(interval_end)))

    return {seat_id: _merge_intervals(intervals) for seat_id, intervals in blocked.items() if intervals}


def cleanup_expired_holds(db: Session, *, now: datetime | None = None) -> int:
    current_time = _as_utc(now or datetime.now(timezone.utc))
    repo = ReservationRepository(db)
    expired_holds = repo.list_expired_payment_holds(now=current_time)
    if not expired_holds:
        return 0

    for reservation in expired_holds:
        reservation.status = ReservationStatus.EXPIRED.value
        db.add(reservation)

    for reservation in expired_holds:
        if reservation.seat is not None:
            sync_seat_operational_status(db, reservation.seat, exclude_reservation_id=reservation.id)
            db.add(reservation.seat)

    db.commit()
    return len(expired_holds)


def check_seat_availability(
    db: Session,
    *,
    seat_id: int,
    start_at: datetime,
    end_at: datetime,
) -> SeatAvailabilityResult:
    start, end = normalize_interval(start_at, end_at)
    seat = SeatRepository(db).get_by_id_with_location(seat_id)
    if seat is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Seat not found")

    blocked_reason = _seat_state_block_reason(seat)
    if blocked_reason is not None:
        return SeatAvailabilityResult(seat=seat, is_available=False, reason=blocked_reason, blocked_intervals=[])

    blocked_intervals = list_blocked_intervals(db, seat_ids=[seat.id], start_at=start, end_at=end).get(seat.id, [])
    if blocked_intervals:
        return SeatAvailabilityResult(
            seat=seat,
            is_available=False,
            reason="Seat already reserved for this time range",
            blocked_intervals=blocked_intervals,
        )

    return SeatAvailabilityResult(seat=seat, is_available=True, blocked_intervals=[])


def list_available_seats(
    db: Session,
    *,
    start_at: datetime,
    end_at: datetime,
    club_id: int | None = None,
    branch_id: int | None = None,
    zone_id: int | None = None,
    seat_type: str | None = None,
) -> list[Seat]:
    start, end = normalize_interval(start_at, end_at)
    seats = SeatRepository(db).list_with_location(club_id=club_id, branch_id=branch_id, zone_id=zone_id)
    if seat_type is not None:
        seats = [seat for seat in seats if seat.seat_type == seat_type]

    candidate_seats = [seat for seat in seats if _seat_state_block_reason(seat) is None]
    blocked_by_seat_id = list_blocked_intervals(
        db,
        seat_ids=[seat.id for seat in candidate_seats],
        start_at=start,
        end_at=end,
    )
    return [seat for seat in candidate_seats if seat.id not in blocked_by_seat_id]


def build_daily_availability_slots(
    db: Session,
    *,
    seat: Seat,
    target_date: date,
) -> list[tuple[datetime, datetime, str]]:
    day_start = datetime.combine(target_date, time.min, tzinfo=timezone.utc)
    day_end = datetime.combine(target_date, time.max, tzinfo=timezone.utc)

    blocked_reason = _seat_state_block_reason(seat)
    if blocked_reason is not None:
        return [(day_start, day_end, seat.operational_status)]

    intervals = list_blocked_intervals(db, seat_ids=[seat.id], start_at=day_start, end_at=day_end).get(seat.id, [])
    slots: list[tuple[datetime, datetime, str]] = []
    cursor = day_start
    for start_at, end_at in intervals:
        start = max(start_at, day_start)
        end = min(end_at, day_end)
        if cursor < start:
            slots.append((cursor, start, "free"))
        slots.append((start, end, "booked"))
        cursor = max(cursor, end)

    if cursor < day_end:
        slots.append((cursor, day_end, "free"))
    if not slots:
        slots.append((day_start, day_end, "free"))
    return slots
