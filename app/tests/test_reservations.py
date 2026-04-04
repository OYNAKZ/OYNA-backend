from datetime import datetime, time, timedelta, timezone

from fastapi.testclient import TestClient

from app.core.constants import ReservationStatus, SessionStatus, UserRole
from app.core.db import SessionLocal
from app.main import app
from app.models import Branch, Club, Reservation, Seat, Session, Zone
from app.tests.conftest import create_user_with_token

client = TestClient(app)


def _seed_club_structure(*, club_name: str = "Demo Club", seat_code: str = "A1") -> dict[str, int]:
    with SessionLocal() as db:
        club = Club(name=club_name, description="Flagship club", is_active=True)
        db.add(club)
        db.flush()

        branch = Branch(
            club_id=club.id,
            name=f"{club_name} Branch",
            address="123 Main St",
            city="Almaty",
            latitude=43.2389,
            longitude=76.8897,
            open_time=time(hour=9),
            close_time=time(hour=23),
            is_active=True,
        )
        db.add(branch)
        db.flush()

        zone = Zone(
            branch_id=branch.id,
            name="VIP",
            zone_type="vip",
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
            x_position=1.0,
            y_position=1.0,
        )
        db.add(seat)
        db.commit()
        db.refresh(seat)
        return {
            "club_id": club.id,
            "branch_id": branch.id,
            "zone_id": zone.id,
            "seat_id": seat.id,
        }


def _seed_reservation(
    *,
    seat_id: int,
    user_id: int,
    start_at: datetime,
    end_at: datetime,
    status: str = ReservationStatus.CONFIRMED.value,
    cancelled_at: datetime | None = None,
) -> Reservation:
    with SessionLocal() as db:
        reservation = Reservation(
            seat_id=seat_id,
            user_id=user_id,
            start_at=start_at,
            end_at=end_at,
            status=status,
            cancelled_at=cancelled_at,
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


def test_create_reservation() -> None:
    user, headers = create_user_with_token(role=UserRole.USER.value, email="demo@example.com", full_name="Demo User")
    structure = _seed_club_structure()

    response = client.post(
        "/api/v1/reservations",
        json={
            "seat_id": structure["seat_id"],
            "start_at": "2026-03-15T10:00:00Z",
            "end_at": "2026-03-15T12:00:00Z",
            "status": "confirmed",
        },
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["user_id"] == user.id
    assert response.json()["seat_id"] == structure["seat_id"]


def test_official_reservation_statuses_are_fixed() -> None:
    assert [status.value for status in ReservationStatus] == [
        "created",
        "confirmed",
        "checked_in",
        "session_started",
        "cancelled",
        "expired",
        "no_show",
        "completed",
    ]


def test_get_reservation_detail_owner_can_view_nested_location() -> None:
    user, headers = create_user_with_token(role=UserRole.USER.value, email="owner-view@example.com")
    structure = _seed_club_structure(club_name="Owner View Club")
    reservation = _seed_reservation(
        seat_id=structure["seat_id"],
        user_id=user.id,
        start_at=datetime(2026, 3, 26, 10, 0, tzinfo=timezone.utc),
        end_at=datetime(2026, 3, 26, 12, 0, tzinfo=timezone.utc),
    )

    response = client.get(f"/api/v1/reservations/{reservation.id}", headers=headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == reservation.id
    assert payload["seat"]["id"] == structure["seat_id"]
    assert payload["seat"]["zone"]["id"] == structure["zone_id"]
    assert payload["seat"]["branch"]["id"] == structure["branch_id"]
    assert payload["seat"]["branch"]["club_id"] == structure["club_id"]


def test_get_reservation_detail_club_admin_can_view_own_club() -> None:
    structure = _seed_club_structure(club_name="Admin Club")
    reservation_owner, _ = create_user_with_token(role=UserRole.USER.value, email="club-user@example.com")
    _, admin_headers = create_user_with_token(
        role=UserRole.CLUB_ADMIN.value,
        email="club-admin-scope@example.com",
        club_id=structure["club_id"],
    )
    reservation = _seed_reservation(
        seat_id=structure["seat_id"],
        user_id=reservation_owner.id,
        start_at=datetime(2026, 3, 26, 13, 0, tzinfo=timezone.utc),
        end_at=datetime(2026, 3, 26, 15, 0, tzinfo=timezone.utc),
    )

    response = client.get(f"/api/v1/reservations/{reservation.id}", headers=admin_headers)

    assert response.status_code == 200
    assert response.json()["id"] == reservation.id


def test_get_reservation_detail_foreign_user_gets_403() -> None:
    owner, owner_headers = create_user_with_token(role=UserRole.USER.value, email="detail-owner@example.com")
    stranger, stranger_headers = create_user_with_token(role=UserRole.USER.value, email="detail-stranger@example.com")
    structure = _seed_club_structure(club_name="Forbidden Club")
    reservation = _seed_reservation(
        seat_id=structure["seat_id"],
        user_id=owner.id,
        start_at=datetime(2026, 3, 26, 16, 0, tzinfo=timezone.utc),
        end_at=datetime(2026, 3, 26, 17, 0, tzinfo=timezone.utc),
    )

    response = client.get(f"/api/v1/reservations/{reservation.id}", headers=stranger_headers)

    assert owner_headers["Authorization"] != stranger_headers["Authorization"]
    assert response.status_code == 403


def test_cancel_reservation_success() -> None:
    user, headers = create_user_with_token(role=UserRole.USER.value, email="cancel-ok@example.com")
    structure = _seed_club_structure(club_name="Cancel Club")
    reservation = _seed_reservation(
        seat_id=structure["seat_id"],
        user_id=user.id,
        start_at=datetime.now(timezone.utc) + timedelta(hours=1),
        end_at=datetime.now(timezone.utc) + timedelta(hours=2),
    )

    response = client.patch(f"/api/v1/reservations/{reservation.id}/cancel", headers=headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == ReservationStatus.CANCELLED.value
    assert payload["cancelled_at"] is not None


def test_cancel_reservation_with_active_session_returns_400() -> None:
    user, headers = create_user_with_token(role=UserRole.USER.value, email="cancel-session@example.com")
    structure = _seed_club_structure(club_name="Session Club")
    reservation = _seed_reservation(
        seat_id=structure["seat_id"],
        user_id=user.id,
        start_at=datetime.now(timezone.utc) + timedelta(hours=1),
        end_at=datetime.now(timezone.utc) + timedelta(hours=2),
        status=ReservationStatus.CHECKED_IN.value,
    )
    _seed_session(
        reservation_id=reservation.id,
        seat_id=structure["seat_id"],
        user_id=user.id,
        started_at=datetime.now(timezone.utc),
        planned_end_at=datetime.now(timezone.utc) + timedelta(hours=1),
        status=SessionStatus.ACTIVE.value,
    )

    response = client.patch(f"/api/v1/reservations/{reservation.id}/cancel", headers=headers)

    assert response.status_code == 400
    assert response.json()["detail"] == "Active session prevents cancellation"


def test_cancel_reservation_too_late_returns_400() -> None:
    user, headers = create_user_with_token(role=UserRole.USER.value, email="cancel-late@example.com")
    structure = _seed_club_structure(club_name="Late Club")
    reservation = _seed_reservation(
        seat_id=structure["seat_id"],
        user_id=user.id,
        start_at=datetime.now(timezone.utc) + timedelta(minutes=10),
        end_at=datetime.now(timezone.utc) + timedelta(hours=1),
    )

    response = client.patch(f"/api/v1/reservations/{reservation.id}/cancel", headers=headers)

    assert response.status_code == 400
    assert response.json()["detail"] == "Cancellation window has closed"
