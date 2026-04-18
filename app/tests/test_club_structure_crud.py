from fastapi.testclient import TestClient

from app.core.constants import UserRole
from app.main import app
from app.tests.conftest import create_user_with_token

client = TestClient(app)


def test_full_club_structure_crud_flow() -> None:
    _, platform_admin_headers = create_user_with_token(
        role=UserRole.PLATFORM_ADMIN.value,
        email="platform-admin@example.com",
    )

    club_response = client.post(
        "/api/v1/clubs",
        json={"name": "OYNA Club", "description": "Main network", "is_active": True},
        headers=platform_admin_headers,
    )
    assert club_response.status_code == 200
    club_id = club_response.json()["id"]
    _, staff_headers = create_user_with_token(role=UserRole.OWNER.value, email="owner@example.com", club_id=club_id)

    branch_response = client.post(
        "/api/v1/branches",
        json={
            "club_id": club_id,
            "name": "Center Branch",
            "address": "Lenina 1",
            "city": "Ekaterinburg",
            "latitude": 56.8389,
            "longitude": 60.6057,
            "open_time": "09:00:00",
            "close_time": "23:00:00",
            "is_active": True,
        },
        headers=staff_headers,
    )
    assert branch_response.status_code == 200
    branch_id = branch_response.json()["id"]

    branches_response = client.get("/api/v1/branches", headers=staff_headers)
    assert branches_response.status_code == 200
    assert len(branches_response.json()) == 1

    zone_response = client.post(
        "/api/v1/zones",
        json={
            "branch_id": branch_id,
            "name": "VIP",
            "zone_type": "console",
            "description": "Premium seats",
            "is_active": True,
        },
        headers=staff_headers,
    )
    assert zone_response.status_code == 200
    zone_id = zone_response.json()["id"]

    seat_response = client.post(
        "/api/v1/seats",
        json={
            "zone_id": zone_id,
            "code": "A-01",
            "seat_type": "ps5",
            "is_active": True,
            "is_maintenance": False,
            "x_position": 10.0,
            "y_position": 20.0,
        },
        headers=staff_headers,
    )
    assert seat_response.status_code == 200
    seat_id = seat_response.json()["id"]

    zones_response = client.get("/api/v1/zones", headers=staff_headers)
    assert zones_response.status_code == 200
    assert len(zones_response.json()) == 1

    seats_response = client.get("/api/v1/seats", headers=staff_headers)
    assert seats_response.status_code == 200
    assert len(seats_response.json()) == 1
    assert seats_response.json()[0]["id"] == seat_id


def test_seat_code_must_be_unique_within_zone() -> None:
    _, platform_admin_headers = create_user_with_token(
        role=UserRole.PLATFORM_ADMIN.value,
        email="platform-admin-2@example.com",
    )

    club_response = client.post(
        "/api/v1/clubs",
        json={"name": "Second Club", "description": None, "is_active": True},
        headers=platform_admin_headers,
    )
    club_id = club_response.json()["id"]
    _, staff_headers = create_user_with_token(role=UserRole.OWNER.value, email="owner-2@example.com", club_id=club_id)

    branch_response = client.post(
        "/api/v1/branches",
        json={
            "club_id": club_id,
            "name": "Second Branch",
            "address": "Mira 10",
            "city": "Perm",
            "latitude": 58.0105,
            "longitude": 56.2502,
            "open_time": "10:00:00",
            "close_time": "22:00:00",
            "is_active": True,
        },
        headers=staff_headers,
    )
    branch_id = branch_response.json()["id"]

    zone_response = client.post(
        "/api/v1/zones",
        json={
            "branch_id": branch_id,
            "name": "PC Hall",
            "zone_type": "pc",
            "description": None,
            "is_active": True,
        },
        headers=staff_headers,
    )
    zone_id = zone_response.json()["id"]

    first_seat = client.post(
        "/api/v1/seats",
        json={"zone_id": zone_id, "code": "B-01", "seat_type": "pc", "is_active": True, "is_maintenance": False},
        headers=staff_headers,
    )
    assert first_seat.status_code == 200

    duplicate_seat = client.post(
        "/api/v1/seats",
        json={"zone_id": zone_id, "code": "B-01", "seat_type": "pc", "is_active": True, "is_maintenance": False},
        headers=staff_headers,
    )
    assert duplicate_seat.status_code == 409
