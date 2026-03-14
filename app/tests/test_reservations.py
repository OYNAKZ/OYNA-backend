from fastapi.testclient import TestClient

from app.core.db import SessionLocal
from app.models import Branch, Club, Seat, User, Zone
from app.main import app


client = TestClient(app)


def _seed_reservation_dependencies() -> tuple[int, int]:
    with SessionLocal() as db:
        user = User(
            full_name="Demo User",
            email="demo@example.com",
            phone="+70000000001",
            password_hash="hashed-password",
        )
        club = Club(name="Demo Club", description="Flagship club", is_active=True)
        db.add_all([user, club])
        db.flush()

        branch = Branch(
            club_id=club.id,
            name="Main Branch",
            address="123 Main St",
            city="Almaty",
            latitude=43.2389,
            longitude=76.8897,
            open_time="09:00:00",
            close_time="23:00:00",
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
        db.refresh(user)
        db.refresh(seat)
        return user.id, seat.id


def test_create_reservation() -> None:
    user_id, seat_id = _seed_reservation_dependencies()

    response = client.post(
        "/api/v1/reservations",
        json={
            "seat_id": seat_id,
            "user_id": user_id,
            "start_at": "2026-03-15T10:00:00Z",
            "end_at": "2026-03-15T12:00:00Z",
            "status": "confirmed",
        },
    )
    assert response.status_code == 200
    assert response.json()["user_id"] == user_id
    assert response.json()["seat_id"] == seat_id
