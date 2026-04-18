from datetime import datetime, time, timedelta, timezone

from fastapi.testclient import TestClient

from app.core.constants import ReservationStatus, ScopeRole, UserRole
from app.core.db import SessionLocal
from app.main import app
from app.models import Branch, Club, Reservation, Seat, StaffAssignment, Zone
from app.tests.conftest import create_user_with_token

client = TestClient(app)


def _seed_structure(club_name: str, branch_name: str, seat_code: str) -> dict[str, int]:
    with SessionLocal() as db:
        club = Club(name=club_name, description=None, is_active=True)
        db.add(club)
        db.flush()
        branch = Branch(
            club_id=club.id,
            name=branch_name,
            address="Address 1",
            city="Almaty",
            latitude=1.0,
            longitude=1.0,
            open_time=time(hour=9),
            close_time=time(hour=23),
            is_active=True,
        )
        db.add(branch)
        db.flush()
        zone = Zone(branch_id=branch.id, name="Main", zone_type="pc", description=None, is_active=True)
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
        return {"club_id": club.id, "branch_id": branch.id, "zone_id": zone.id, "seat_id": seat.id}


def _seed_second_branch(club_id: int, branch_name: str, seat_code: str) -> dict[str, int]:
    with SessionLocal() as db:
        branch = Branch(
            club_id=club_id,
            name=branch_name,
            address="Address 2",
            city="Almaty",
            latitude=2.0,
            longitude=2.0,
            open_time=time(hour=9),
            close_time=time(hour=23),
            is_active=True,
        )
        db.add(branch)
        db.flush()
        zone = Zone(branch_id=branch.id, name="Side", zone_type="pc", description=None, is_active=True)
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
        return {"club_id": club_id, "branch_id": branch.id, "zone_id": zone.id, "seat_id": seat.id}


def _create_assignment(*, user_id: int, club_id: int, branch_id: int | None, role_in_scope: str, is_active: bool = True) -> None:
    with SessionLocal() as db:
        db.add(
            StaffAssignment(
                user_id=user_id,
                club_id=club_id,
                branch_id=branch_id,
                role_in_scope=role_in_scope,
                is_active=is_active,
            )
        )
        db.commit()


def _seed_reservation(*, seat_id: int, user_id: int) -> Reservation:
    with SessionLocal() as db:
        reservation = Reservation(
            seat_id=seat_id,
            user_id=user_id,
            start_at=datetime.now(timezone.utc) - timedelta(minutes=5),
            end_at=datetime.now(timezone.utc) + timedelta(hours=1),
            status=ReservationStatus.CONFIRMED.value,
        )
        db.add(reservation)
        db.commit()
        db.refresh(reservation)
        return reservation


def test_club_admin_cannot_create_branch_for_foreign_club() -> None:
    allowed = _seed_structure("Allowed Club", "Allowed Branch", "A1")
    blocked = _seed_structure("Blocked Club", "Blocked Branch", "B1")
    admin, admin_headers = create_user_with_token(role=UserRole.CLUB_ADMIN.value, email="club-admin-auth@example.com")
    _create_assignment(
        user_id=admin.id,
        club_id=allowed["club_id"],
        branch_id=allowed["branch_id"],
        role_in_scope=ScopeRole.CLUB_ADMIN.value,
    )

    response = client.post(
        "/api/v1/branches",
        json={
            "club_id": blocked["club_id"],
            "name": "Should Fail",
            "address": "Nope",
            "city": "Astana",
            "latitude": 1.0,
            "longitude": 1.0,
            "open_time": "10:00:00",
            "close_time": "22:00:00",
            "is_active": True,
        },
        headers=admin_headers,
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Insufficient scope"


def test_branch_scoped_admin_cannot_create_zone_for_other_branch() -> None:
    structure_a = _seed_structure("Club A", "Branch A", "A1")
    structure_b = _seed_second_branch(structure_a["club_id"], "Branch B", "B1")
    admin, admin_headers = create_user_with_token(role=UserRole.CLUB_ADMIN.value, email="branch-admin-auth@example.com")
    _create_assignment(
        user_id=admin.id,
        club_id=structure_a["club_id"],
        branch_id=structure_a["branch_id"],
        role_in_scope=ScopeRole.CLUB_ADMIN.value,
    )

    response = client.post(
        "/api/v1/zones",
        json={
            "branch_id": structure_b["branch_id"],
            "name": "Blocked Zone",
            "zone_type": "pc",
            "description": None,
            "is_active": True,
        },
        headers=admin_headers,
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Insufficient scope"


def test_branch_scoped_admin_cannot_start_session_in_other_branch() -> None:
    allowed = _seed_structure("Allowed Ops Club", "Allowed Ops Branch", "A1")
    blocked = _seed_second_branch(allowed["club_id"], "Blocked Ops Branch", "B1")
    visitor, _ = create_user_with_token(role=UserRole.USER.value, email="visitor-auth@example.com")
    admin, admin_headers = create_user_with_token(role=UserRole.CLUB_ADMIN.value, email="session-admin-auth@example.com")
    _create_assignment(
        user_id=admin.id,
        club_id=allowed["club_id"],
        branch_id=allowed["branch_id"],
        role_in_scope=ScopeRole.CLUB_ADMIN.value,
    )
    foreign_reservation = _seed_reservation(seat_id=blocked["seat_id"], user_id=visitor.id)

    response = client.post(
        "/api/v1/sessions",
        json={
            "reservation_id": foreign_reservation.id,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "planned_end_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
        },
        headers=admin_headers,
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Insufficient scope"


def test_owner_can_manage_resources_for_assigned_club() -> None:
    with SessionLocal() as db:
        club = Club(name="Owner Managed Club", description=None, is_active=True)
        db.add(club)
        db.commit()
        db.refresh(club)
        club_id = club.id

    _, owner_headers = create_user_with_token(
        role=UserRole.OWNER.value,
        email="owner-managed@example.com",
        club_id=club_id,
    )

    response = client.post(
        "/api/v1/branches",
        json={
            "club_id": club_id,
            "name": "Owner Branch",
            "address": "Managed",
            "city": "Perm",
            "latitude": 1.0,
            "longitude": 1.0,
            "open_time": "09:00:00",
            "close_time": "23:00:00",
            "is_active": True,
        },
        headers=owner_headers,
    )

    assert response.status_code == 200
    assert response.json()["club_id"] == club_id


def test_platform_admin_bypasses_scope_for_session_creation() -> None:
    structure = _seed_structure("Platform Club", "Platform Branch", "P1")
    visitor, _ = create_user_with_token(role=UserRole.USER.value, email="platform-visitor@example.com")
    _, admin_headers = create_user_with_token(role=UserRole.PLATFORM_ADMIN.value, email="platform-admin-auth@example.com")
    reservation = _seed_reservation(seat_id=structure["seat_id"], user_id=visitor.id)

    response = client.post(
        "/api/v1/sessions",
        json={
            "reservation_id": reservation.id,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "planned_end_at": (datetime.now(timezone.utc) + timedelta(minutes=30)).isoformat(),
        },
        headers=admin_headers,
    )

    assert response.status_code == 200
    assert response.json()["reservation_id"] == reservation.id


def test_regular_user_denied_owner_and_operations_endpoints() -> None:
    _, user_headers = create_user_with_token(role=UserRole.USER.value, email="plain-user-auth@example.com")

    owner_response = client.get("/api/v1/owner/clubs", headers=user_headers)
    operations_response = client.get("/api/v1/operations/summary", headers=user_headers)

    assert owner_response.status_code == 403
    assert operations_response.status_code == 403


def test_user_cannot_read_another_profile_but_platform_admin_can_list_users() -> None:
    user, user_headers = create_user_with_token(role=UserRole.USER.value, email="profile-owner@example.com")
    other, _ = create_user_with_token(role=UserRole.USER.value, email="profile-other@example.com")
    _, admin_headers = create_user_with_token(role=UserRole.PLATFORM_ADMIN.value, email="users-admin@example.com")

    forbidden = client.get(f"/api/v1/users/{other.id}", headers=user_headers)
    allowed = client.get("/api/v1/users", headers=admin_headers)
    me = client.get(f"/api/v1/users/{user.id}", headers=user_headers)

    assert forbidden.status_code == 403
    assert forbidden.json()["detail"] == "Insufficient scope"
    assert allowed.status_code == 200
    assert me.status_code == 200


def test_inactive_assignment_blocks_branch_scoped_admin() -> None:
    structure = _seed_structure("Inactive Scope Club", "Inactive Scope Branch", "I1")
    admin, admin_headers = create_user_with_token(role=UserRole.CLUB_ADMIN.value, email="inactive-admin@example.com")
    _create_assignment(
        user_id=admin.id,
        club_id=structure["club_id"],
        branch_id=structure["branch_id"],
        role_in_scope=ScopeRole.CLUB_ADMIN.value,
        is_active=False,
    )

    response = client.post(
        "/api/v1/zones",
        json={
            "branch_id": structure["branch_id"],
            "name": "Should Not Work",
            "zone_type": "pc",
            "description": None,
            "is_active": True,
        },
        headers=admin_headers,
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Insufficient scope"
