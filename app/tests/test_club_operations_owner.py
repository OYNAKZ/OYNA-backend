from datetime import datetime, time, timedelta, timezone

from fastapi.testclient import TestClient

from app.core.constants import ReservationStatus, ScopeRole, SeatOperationalStatus, SessionStatus, UserRole
from app.core.db import SessionLocal
from app.main import app
from app.models import Branch, Club, Reservation, Seat, Session, StaffAssignment, Zone
from app.tests.conftest import create_user_with_token

client = TestClient(app)


def _seed_structure(club_name: str, seat_code: str = "A1") -> dict[str, int]:
    with SessionLocal() as db:
        club = Club(name=club_name, description=None, is_active=True)
        db.add(club)
        db.flush()
        branch = Branch(
            club_id=club.id,
            name=f"{club_name} Branch",
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
            operational_status=SeatOperationalStatus.AVAILABLE.value,
        )
        db.add(seat)
        db.commit()
        return {"club_id": club.id, "branch_id": branch.id, "zone_id": zone.id, "seat_id": seat.id}


def _create_assignment(*, user_id: int, club_id: int, branch_id: int | None, role_in_scope: str) -> None:
    with SessionLocal() as db:
        db.add(
            StaffAssignment(
                user_id=user_id,
                club_id=club_id,
                branch_id=branch_id,
                role_in_scope=role_in_scope,
                is_active=True,
            )
        )
        db.commit()


def _seed_reservation(*, seat_id: int, user_id: int, start_at: datetime, end_at: datetime) -> Reservation:
    with SessionLocal() as db:
        reservation = Reservation(
            seat_id=seat_id,
            user_id=user_id,
            start_at=start_at,
            end_at=end_at,
            status=ReservationStatus.CONFIRMED.value,
        )
        db.add(reservation)
        seat = db.get(Seat, seat_id)
        seat.operational_status = SeatOperationalStatus.RESERVED.value
        db.add(seat)
        db.commit()
        db.refresh(reservation)
        return reservation


def test_club_admin_operational_lifecycle() -> None:
    structure = _seed_structure("Ops Club")
    visitor, _ = create_user_with_token(role=UserRole.USER.value, email="visitor@example.com")
    admin, admin_headers = create_user_with_token(role=UserRole.CLUB_ADMIN.value, email="ops-admin@example.com")
    _create_assignment(
        user_id=admin.id,
        club_id=structure["club_id"],
        branch_id=structure["branch_id"],
        role_in_scope=ScopeRole.CLUB_ADMIN.value,
    )
    reservation = _seed_reservation(
        seat_id=structure["seat_id"],
        user_id=visitor.id,
        start_at=datetime.now(timezone.utc) - timedelta(minutes=5),
        end_at=datetime.now(timezone.utc) + timedelta(hours=1),
    )

    list_response = client.get("/api/v1/operations/reservations?page=1&page_size=10", headers=admin_headers)
    assert list_response.status_code == 200
    assert list_response.json()["total"] == 1

    check_in = client.patch(f"/api/v1/operations/reservations/{reservation.id}/check-in", headers=admin_headers)
    assert check_in.status_code == 200
    assert check_in.json()["status"] == ReservationStatus.CHECKED_IN.value

    start_session = client.post(
        f"/api/v1/operations/reservations/{reservation.id}/start-session",
        headers=admin_headers,
    )
    assert start_session.status_code == 200
    session_id = start_session.json()["id"]

    with SessionLocal() as db:
        seat = db.get(Seat, structure["seat_id"])
        assert seat.operational_status == SeatOperationalStatus.OCCUPIED.value

    finish = client.patch(f"/api/v1/operations/sessions/{session_id}/finish", headers=admin_headers)
    assert finish.status_code == 200
    assert finish.json()["status"] == SessionStatus.FINISHED.value

    repeated = client.patch(f"/api/v1/operations/sessions/{session_id}/finish", headers=admin_headers)
    assert repeated.status_code == 409


def test_club_admin_check_in_forbidden_out_of_scope() -> None:
    structure_a = _seed_structure("Allowed Club", "A1")
    structure_b = _seed_structure("Blocked Club", "B1")
    visitor, _ = create_user_with_token(role=UserRole.USER.value, email="scope-visitor@example.com")
    admin, admin_headers = create_user_with_token(role=UserRole.CLUB_ADMIN.value, email="scope-admin@example.com")
    _create_assignment(
        user_id=admin.id,
        club_id=structure_a["club_id"],
        branch_id=structure_a["branch_id"],
        role_in_scope=ScopeRole.CLUB_ADMIN.value,
    )
    foreign_reservation = _seed_reservation(
        seat_id=structure_b["seat_id"],
        user_id=visitor.id,
        start_at=datetime.now(timezone.utc),
        end_at=datetime.now(timezone.utc) + timedelta(hours=2),
    )

    response = client.patch(
        f"/api/v1/operations/reservations/{foreign_reservation.id}/check-in",
        headers=admin_headers,
    )
    assert response.status_code == 403


def test_seat_maintenance_blocks_new_reservations_and_tracks_history() -> None:
    structure = _seed_structure("Maintenance Club")
    visitor, visitor_headers = create_user_with_token(role=UserRole.USER.value, email="maint-user@example.com")
    admin, admin_headers = create_user_with_token(role=UserRole.CLUB_ADMIN.value, email="maint-admin@example.com")
    _create_assignment(
        user_id=admin.id,
        club_id=structure["club_id"],
        branch_id=structure["branch_id"],
        role_in_scope=ScopeRole.CLUB_ADMIN.value,
    )

    status_response = client.patch(
        f"/api/v1/operations/seats/{structure['seat_id']}/status",
        json={"operational_status": "maintenance", "reason": "GPU replacement"},
        headers=admin_headers,
    )
    assert status_response.status_code == 200
    assert status_response.json()["to_status"] == SeatOperationalStatus.MAINTENANCE.value

    reservation_response = client.post(
        "/api/v1/reservations",
        json={
            "seat_id": structure["seat_id"],
            "start_at": "2026-04-01T10:00:00Z",
            "end_at": "2026-04-01T12:00:00Z",
        },
        headers=visitor_headers,
    )
    assert reservation_response.status_code == 409

    history_response = client.get(
        f"/api/v1/operations/seats/{structure['seat_id']}/status-history",
        headers=admin_headers,
    )
    assert history_response.status_code == 200
    assert history_response.json()[0]["reason"] == "GPU replacement"
    assert visitor.id > 0


def test_owner_overview_analytics_and_staff_assignment() -> None:
    structure = _seed_structure("Owner Club")
    owner, owner_headers = create_user_with_token(
        role=UserRole.OWNER.value,
        email="owner-stage6@example.com",
        club_id=structure["club_id"],
    )
    admin, _ = create_user_with_token(role=UserRole.CLUB_ADMIN.value, email="assign-admin@example.com")
    user, _ = create_user_with_token(role=UserRole.USER.value, email="analytics-user@example.com")
    reservation = _seed_reservation(
        seat_id=structure["seat_id"],
        user_id=user.id,
        start_at=datetime.now(timezone.utc) - timedelta(hours=1),
        end_at=datetime.now(timezone.utc) + timedelta(hours=1),
    )
    with SessionLocal() as db:
        db.add(
            Session(
                reservation_id=reservation.id,
                seat_id=structure["seat_id"],
                user_id=user.id,
                started_at=datetime.now(timezone.utc) - timedelta(minutes=30),
                planned_end_at=datetime.now(timezone.utc) + timedelta(minutes=30),
                status=SessionStatus.ACTIVE.value,
            )
        )
        seat = db.get(Seat, structure["seat_id"])
        seat.operational_status = SeatOperationalStatus.OCCUPIED.value
        db.add(seat)
        db.commit()

    clubs_response = client.get("/api/v1/owner/clubs", headers=owner_headers)
    assert clubs_response.status_code == 200
    assert clubs_response.json()[0]["club"]["id"] == structure["club_id"]

    analytics_response = client.get("/api/v1/owner/analytics?period=30d", headers=owner_headers)
    assert analytics_response.status_code == 200
    assert analytics_response.json()["active_sessions"] == 1

    assign_response = client.post(
        "/api/v1/owner/staff-assignments",
        json={
            "user_id": admin.id,
            "club_id": structure["club_id"],
            "branch_id": structure["branch_id"],
            "role_in_scope": UserRole.CLUB_ADMIN.value,
        },
        headers=owner_headers,
    )
    assert assign_response.status_code == 200
    assert assign_response.json()["user_id"] == admin.id

    scope_response = client.get(f"/api/v1/owner/staff/{admin.id}/scope", headers=owner_headers)
    assert scope_response.status_code == 200
    assert scope_response.json()["assignments"][0]["club_id"] == structure["club_id"]
    assert owner.id > 0


def test_owner_cannot_access_foreign_club_analytics() -> None:
    structure_a = _seed_structure("Owner Visible")
    structure_b = _seed_structure("Owner Hidden")
    _, owner_headers = create_user_with_token(
        role=UserRole.OWNER.value,
        email="owner-visible@example.com",
        club_id=structure_a["club_id"],
    )

    response = client.get(f"/api/v1/owner/analytics?club_id={structure_b['club_id']}&period=30d", headers=owner_headers)
    assert response.status_code == 403
