from datetime import datetime, time, timezone

from fastapi.testclient import TestClient

from app.core.constants import ReservationStatus, SessionStatus, UserRole
from app.core.db import SessionLocal
from app.main import app
from app.models import Branch, Club, Reservation, Seat, Session, Zone
from app.tests.conftest import create_user_with_token

client = TestClient(app)


def _seed_seat_structure(*, club_name: str, seat_code: str) -> tuple[int, int]:
    with SessionLocal() as db:
        club = Club(name=club_name, description=None, is_active=True)
        db.add(club)
        db.flush()

        branch = Branch(
            club_id=club.id,
            name=f"{club_name} Branch",
            address="Any street",
            city="Astana",
            latitude=51.1694,
            longitude=71.4491,
            open_time=time(hour=0),
            close_time=time(hour=23, minute=59),
            is_active=True,
        )
        db.add(branch)
        db.flush()

        zone = Zone(
            branch_id=branch.id,
            name="Hall",
            zone_type="pc",
            description=None,
            is_active=True,
        )
        db.add(zone)
        db.flush()

        seat = Seat(
            zone_id=zone.id,
            code=seat_code,
            seat_type="pc",
            is_active=True,
            is_maintenance=False,
        )
        db.add(seat)
        db.commit()
        db.refresh(seat)
        return club.id, seat.id


def _seed_reservation(
    *,
    seat_id: int,
    user_id: int,
    start_at: datetime,
    end_at: datetime,
    status: str = ReservationStatus.CONFIRMED.value,
) -> Reservation:
    with SessionLocal() as db:
        reservation = Reservation(
            seat_id=seat_id,
            user_id=user_id,
            start_at=start_at,
            end_at=end_at,
            status=status,
        )
        db.add(reservation)
        db.commit()
        db.refresh(reservation)
        return reservation


def _seed_session(
    *,
    reservation_id: int,
    seat_id: int,
    user_id: int,
    started_at: datetime,
    planned_end_at: datetime,
    ended_at: datetime | None = None,
    status: str = SessionStatus.ACTIVE.value,
) -> Session:
    with SessionLocal() as db:
        session = Session(
            reservation_id=reservation_id,
            seat_id=seat_id,
            user_id=user_id,
            started_at=started_at,
            planned_end_at=planned_end_at,
            ended_at=ended_at,
            status=status,
        )
        db.add(session)
        db.commit()
        db.refresh(session)
        return session


def test_seat_availability_free_for_full_day() -> None:
    _, headers = create_user_with_token(role=UserRole.USER.value, email="availability-free@example.com")
    _, seat_id = _seed_seat_structure(club_name="Free Club", seat_code="F-01")

    response = client.get(f"/api/v1/seats/{seat_id}/availability?date=2026-03-27", headers=headers)

    assert response.status_code == 200
    slots = response.json()["slots"]
    assert len(slots) == 1
    assert slots[0]["status"] == "free"


def test_seat_availability_partially_booked() -> None:
    user, headers = create_user_with_token(role=UserRole.USER.value, email="availability-partial@example.com")
    _, seat_id = _seed_seat_structure(club_name="Partial Club", seat_code="P-01")
    reservation = _seed_reservation(
        seat_id=seat_id,
        user_id=user.id,
        start_at=datetime(2026, 3, 27, 10, 0, tzinfo=timezone.utc),
        end_at=datetime(2026, 3, 27, 12, 0, tzinfo=timezone.utc),
    )
    _seed_session(
        reservation_id=reservation.id,
        seat_id=seat_id,
        user_id=user.id,
        started_at=datetime(2026, 3, 27, 14, 0, tzinfo=timezone.utc),
        planned_end_at=datetime(2026, 3, 27, 15, 30, tzinfo=timezone.utc),
        ended_at=datetime(2026, 3, 27, 15, 0, tzinfo=timezone.utc),
        status=SessionStatus.COMPLETED.value,
    )

    response = client.get(f"/api/v1/seats/{seat_id}/availability?date=2026-03-27", headers=headers)

    assert response.status_code == 200
    slots = response.json()["slots"]
    booked_slots = [slot for slot in slots if slot["status"] == "booked"]
    assert len(booked_slots) == 2
    assert booked_slots[0]["start"] == "2026-03-27T10:00:00Z"
    assert booked_slots[0]["end"] == "2026-03-27T12:00:00Z"
    assert booked_slots[1]["start"] == "2026-03-27T14:00:00Z"
    assert booked_slots[1]["end"] == "2026-03-27T15:00:00Z"


def test_seat_availability_fully_booked() -> None:
    user, headers = create_user_with_token(role=UserRole.USER.value, email="availability-full@example.com")
    _, seat_id = _seed_seat_structure(club_name="Full Club", seat_code="X-01")
    _seed_reservation(
        seat_id=seat_id,
        user_id=user.id,
        start_at=datetime(2026, 3, 27, 0, 0, tzinfo=timezone.utc),
        end_at=datetime(2026, 3, 27, 23, 59, 59, 999999, tzinfo=timezone.utc),
    )

    response = client.get(f"/api/v1/seats/{seat_id}/availability?date=2026-03-27", headers=headers)

    assert response.status_code == 200
    slots = response.json()["slots"]
    assert len(slots) == 1
    assert slots[0]["status"] == "booked"
