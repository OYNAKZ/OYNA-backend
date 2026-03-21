from datetime import time

from fastapi.testclient import TestClient

from app.core.constants import UserRole
from app.core.db import SessionLocal
from app.main import app
from app.models import Branch, Club, Seat, Zone
from app.tests.conftest import create_user_with_token

client = TestClient(app)


def _seed_reservation_dependencies() -> tuple[int, int, dict[str, str]]:
    user, headers = create_user_with_token(role=UserRole.USER.value, email="demo@example.com", full_name="Demo User")

    with SessionLocal() as db:
        club = Club(name="Demo Club", description="Flagship club", is_active=True)
        db.add(club)
        db.flush()

        branch = Branch(
            club_id=club.id,
            name="Main Branch",
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
            code="A1",
            seat_type="pc",
            is_active=True,
            is_maintenance=False,
            x_position=1.0,
            y_position=1.0,
        )
        db.add(seat)
        db.commit()
        db.refresh(seat)
        return user.id, seat.id, headers


def test_create_reservation() -> None:
    user_id, seat_id, headers = _seed_reservation_dependencies()

    response = client.post(
        "/api/v1/reservations",
        json={
            "seat_id": seat_id,
            "start_at": "2026-03-15T10:00:00Z",
            "end_at": "2026-03-15T12:00:00Z",
            "status": "confirmed",
        },
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["user_id"] == user_id
    assert response.json()["seat_id"] == seat_id
