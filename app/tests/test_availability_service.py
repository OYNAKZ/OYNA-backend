from datetime import datetime, time, timezone

from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.core.constants import ReservationStatus, SeatOperationalStatus, SessionStatus, UserRole
from app.core.db import SessionLocal
from app.main import app
from app.models import Branch, Club, Reservation, Seat, Session, Zone
from app.services.availability import check_seat_availability, list_available_seats
from app.tests.conftest import create_user_with_token

client = TestClient(app)


def _seed_structure(*, club_name: str, branch_name: str, zone_name: str, seat_code: str) -> dict[str, int]:
    with SessionLocal() as db:
        club = Club(name=club_name, description=None, is_active=True)
        db.add(club)
        db.flush()
        branch = Branch(
            club_id=club.id,
            name=branch_name,
            address="Address 1",
            city="Astana",
            latitude=1.0,
            longitude=1.0,
            open_time=time(hour=0),
            close_time=time(hour=23, minute=59),
            is_active=True,
        )
        db.add(branch)
        db.flush()
        zone = Zone(branch_id=branch.id, name=zone_name, zone_type="pc", description=None, is_active=True)
        db.add(zone)
        db.flush()
        seat = Seat(
            zone_id=zone.id,
            code=seat_code,
            seat_type="pc",
            is_active=True,
            is_maintenance=False,
            operational_status=SeatOperationalStatus.AVAILABLE.value,
        )
        db.add(seat)
        db.commit()
        db.refresh(seat)
        return {"club_id": club.id, "branch_id": branch.id, "zone_id": zone.id, "seat_id": seat.id}


def _seed_reservation(
    *,
    seat_id: int,
    user_id: int,
    start_at: datetime,
    end_at: datetime,
    status: str = ReservationStatus.CONFIRMED.value,
) -> None:
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


def _seed_session(
    *,
    reservation_id: int,
    seat_id: int,
    user_id: int,
    started_at: datetime,
    planned_end_at: datetime,
    ended_at: datetime | None = None,
    status: str = SessionStatus.ACTIVE.value,
) -> None:
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


def test_check_seat_availability_allows_exact_end_to_start_adjacency() -> None:
    structure = _seed_structure(
        club_name="Adjacency Club",
        branch_name="Main Branch",
        zone_name="Hall",
        seat_code="A1",
    )
    user, _ = create_user_with_token(role=UserRole.USER.value, email="adjacency-user@example.com")
    _seed_reservation(
        seat_id=structure["seat_id"],
        user_id=user.id,
        start_at=datetime(2026, 4, 20, 10, 0, tzinfo=timezone.utc),
        end_at=datetime(2026, 4, 20, 12, 0, tzinfo=timezone.utc),
    )

    with SessionLocal() as db:
        result = check_seat_availability(
            db,
            seat_id=structure["seat_id"],
            start_at=datetime(2026, 4, 20, 12, 0, tzinfo=timezone.utc),
            end_at=datetime(2026, 4, 20, 13, 0, tzinfo=timezone.utc),
        )

    assert result.is_available is True


def test_check_seat_availability_rejects_full_and_partial_and_nested_overlap() -> None:
    structure = _seed_structure(
        club_name="Overlap Club",
        branch_name="Main Branch",
        zone_name="Hall",
        seat_code="B1",
    )
    user, _ = create_user_with_token(role=UserRole.USER.value, email="overlap-user@example.com")
    _seed_reservation(
        seat_id=structure["seat_id"],
        user_id=user.id,
        start_at=datetime(2026, 4, 20, 10, 0, tzinfo=timezone.utc),
        end_at=datetime(2026, 4, 20, 12, 0, tzinfo=timezone.utc),
    )

    with SessionLocal() as db:
        full = check_seat_availability(
            db,
            seat_id=structure["seat_id"],
            start_at=datetime(2026, 4, 20, 9, 0, tzinfo=timezone.utc),
            end_at=datetime(2026, 4, 20, 13, 0, tzinfo=timezone.utc),
        )
        partial = check_seat_availability(
            db,
            seat_id=structure["seat_id"],
            start_at=datetime(2026, 4, 20, 11, 0, tzinfo=timezone.utc),
            end_at=datetime(2026, 4, 20, 13, 0, tzinfo=timezone.utc),
        )
        nested = check_seat_availability(
            db,
            seat_id=structure["seat_id"],
            start_at=datetime(2026, 4, 20, 10, 30, tzinfo=timezone.utc),
            end_at=datetime(2026, 4, 20, 11, 30, tzinfo=timezone.utc),
        )

    assert full.is_available is False
    assert partial.is_available is False
    assert nested.is_available is False
    assert full.reason == "Seat already reserved for this time range"


def test_check_seat_availability_rejects_active_session_overlap() -> None:
    structure = _seed_structure(
        club_name="Session Overlap Club",
        branch_name="Main Branch",
        zone_name="Hall",
        seat_code="C1",
    )
    user, _ = create_user_with_token(role=UserRole.USER.value, email="session-overlap-user@example.com")
    with SessionLocal() as db:
        reservation = Reservation(
            seat_id=structure["seat_id"],
            user_id=user.id,
            start_at=datetime(2026, 4, 20, 8, 0, tzinfo=timezone.utc),
            end_at=datetime(2026, 4, 20, 9, 0, tzinfo=timezone.utc),
            status=ReservationStatus.SESSION_STARTED.value,
        )
        db.add(reservation)
        db.commit()
        db.refresh(reservation)
        reservation_id = reservation.id
    _seed_session(
        reservation_id=reservation_id,
        seat_id=structure["seat_id"],
        user_id=user.id,
        started_at=datetime(2026, 4, 20, 10, 0, tzinfo=timezone.utc),
        planned_end_at=datetime(2026, 4, 20, 12, 0, tzinfo=timezone.utc),
        status=SessionStatus.ACTIVE.value,
    )

    with SessionLocal() as db:
        result = check_seat_availability(
            db,
            seat_id=structure["seat_id"],
            start_at=datetime(2026, 4, 20, 11, 0, tzinfo=timezone.utc),
            end_at=datetime(2026, 4, 20, 11, 30, tzinfo=timezone.utc),
        )

    assert result.is_available is False
    assert result.reason == "Seat already reserved for this time range"


def test_check_seat_availability_rejects_inactive_and_maintenance_states() -> None:
    inactive = _seed_structure(
        club_name="Inactive Club",
        branch_name="Main Branch",
        zone_name="Hall",
        seat_code="D1",
    )
    maintenance = _seed_structure(
        club_name="Maintenance Club",
        branch_name="Main Branch",
        zone_name="Hall",
        seat_code="E1",
    )
    with SessionLocal() as db:
        inactive_seat = db.get(Seat, inactive["seat_id"])
        maintenance_seat = db.get(Seat, maintenance["seat_id"])
        inactive_seat.is_active = False
        maintenance_seat.is_maintenance = True
        maintenance_seat.operational_status = SeatOperationalStatus.MAINTENANCE.value
        db.add_all([inactive_seat, maintenance_seat])
        db.commit()

    with SessionLocal() as db:
        inactive_result = check_seat_availability(
            db,
            seat_id=inactive["seat_id"],
            start_at=datetime(2026, 4, 20, 10, 0, tzinfo=timezone.utc),
            end_at=datetime(2026, 4, 20, 11, 0, tzinfo=timezone.utc),
        )
        maintenance_result = check_seat_availability(
            db,
            seat_id=maintenance["seat_id"],
            start_at=datetime(2026, 4, 20, 10, 0, tzinfo=timezone.utc),
            end_at=datetime(2026, 4, 20, 11, 0, tzinfo=timezone.utc),
        )

    assert inactive_result.is_available is False
    assert inactive_result.reason == "Seat is inactive"
    assert maintenance_result.is_available is False
    assert maintenance_result.reason == "Seat is under maintenance"


def test_list_available_seats_filters_out_overlapping_and_returns_in_scope_matches() -> None:
    structure_a = _seed_structure(
        club_name="Listing Club",
        branch_name="Main Branch",
        zone_name="Hall A",
        seat_code="F1",
    )
    structure_b = _seed_structure(
        club_name="Listing Club 2",
        branch_name="Second Branch",
        zone_name="Hall B",
        seat_code="F2",
    )
    user, _ = create_user_with_token(role=UserRole.USER.value, email="listing-user@example.com")
    _seed_reservation(
        seat_id=structure_a["seat_id"],
        user_id=user.id,
        start_at=datetime(2026, 4, 20, 10, 0, tzinfo=timezone.utc),
        end_at=datetime(2026, 4, 20, 12, 0, tzinfo=timezone.utc),
    )

    with SessionLocal() as db:
        available = list_available_seats(
            db,
            branch_id=structure_a["branch_id"],
            start_at=datetime(2026, 4, 20, 10, 30, tzinfo=timezone.utc),
            end_at=datetime(2026, 4, 20, 11, 0, tzinfo=timezone.utc),
        )
        available_by_club = list_available_seats(
            db,
            club_id=structure_b["club_id"],
            start_at=datetime(2026, 4, 20, 10, 30, tzinfo=timezone.utc),
            end_at=datetime(2026, 4, 20, 11, 0, tzinfo=timezone.utc),
        )
        available_other_branch = list_available_seats(
            db,
            branch_id=structure_b["branch_id"],
            start_at=datetime(2026, 4, 20, 10, 30, tzinfo=timezone.utc),
            end_at=datetime(2026, 4, 20, 11, 0, tzinfo=timezone.utc),
        )

    assert available == []
    assert [seat.id for seat in available_by_club] == [structure_b["seat_id"]]
    assert [seat.id for seat in available_other_branch] == [structure_b["seat_id"]]


def test_list_available_seats_rejects_invalid_interval() -> None:
    structure = _seed_structure(
        club_name="Invalid Interval Club",
        branch_name="Main Branch",
        zone_name="Hall",
        seat_code="G1",
    )

    with SessionLocal() as db:
        try:
            list_available_seats(
                db,
                zone_id=structure["zone_id"],
                start_at=datetime(2026, 4, 20, 12, 0, tzinfo=timezone.utc),
                end_at=datetime(2026, 4, 20, 12, 0, tzinfo=timezone.utc),
            )
        except HTTPException as exc:
            assert exc.status_code == 422
            assert exc.detail == "end_at must be after start_at"
        else:
            raise AssertionError("Expected invalid interval to raise HTTPException")


def test_reservation_creation_uses_centralized_availability_for_adjacency() -> None:
    user, headers = create_user_with_token(role=UserRole.USER.value, email="reservation-adjacency@example.com")
    structure = _seed_structure(
        club_name="Reservation Availability Club",
        branch_name="Main Branch",
        zone_name="Hall",
        seat_code="H1",
    )
    _seed_reservation(
        seat_id=structure["seat_id"],
        user_id=user.id,
        start_at=datetime(2026, 4, 20, 10, 0, tzinfo=timezone.utc),
        end_at=datetime(2026, 4, 20, 12, 0, tzinfo=timezone.utc),
    )

    response = client.post(
        "/api/v1/reservations",
        json={
            "seat_id": structure["seat_id"],
            "start_at": "2026-04-20T12:00:00Z",
            "end_at": "2026-04-20T13:00:00Z",
            "status": "confirmed",
        },
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["seat_id"] == structure["seat_id"]
