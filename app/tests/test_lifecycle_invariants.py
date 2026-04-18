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


def _seed_reservation(
    *,
    seat_id: int,
    user_id: int,
    start_at: datetime,
    end_at: datetime,
    status: str = ReservationStatus.CONFIRMED.value,
    expires_at: datetime | None = None,
) -> Reservation:
    with SessionLocal() as db:
        reservation = Reservation(
            seat_id=seat_id,
            user_id=user_id,
            start_at=start_at,
            end_at=end_at,
            status=status,
            expires_at=expires_at,
        )
        db.add(reservation)
        seat = db.get(Seat, seat_id)
        if seat is not None:
            seat.operational_status = SeatOperationalStatus.RESERVED.value
            db.add(seat)
        db.commit()
        db.refresh(reservation)
        return reservation


def _staff_headers_for_structure(structure: dict[str, int], email: str = "ops@example.com") -> dict[str, str]:
    admin, headers = create_user_with_token(role=UserRole.CLUB_ADMIN.value, email=email)
    _create_assignment(
        user_id=admin.id,
        club_id=structure["club_id"],
        branch_id=structure["branch_id"],
        role_in_scope=ScopeRole.CLUB_ADMIN.value,
    )
    return headers


def test_check_in_after_reservation_expired_returns_409() -> None:
    structure = _seed_structure("Expired Checkin Club")
    visitor, _ = create_user_with_token(role=UserRole.USER.value, email="expired-visitor@example.com")
    admin_headers = _staff_headers_for_structure(structure, "expired-admin@example.com")
    reservation = _seed_reservation(
        seat_id=structure["seat_id"],
        user_id=visitor.id,
        start_at=datetime.now(timezone.utc) - timedelta(minutes=5),
        end_at=datetime.now(timezone.utc) + timedelta(hours=1),
        expires_at=datetime.now(timezone.utc) - timedelta(minutes=1),
    )

    response = client.patch(f"/api/v1/operations/reservations/{reservation.id}/check-in", headers=admin_headers)

    assert response.status_code == 409
    assert response.json()["detail"] == "Reservation is expired"


def test_cancelling_after_session_started_returns_409() -> None:
    user, headers = create_user_with_token(role=UserRole.USER.value, email="started-user@example.com")
    structure = _seed_structure("Cancel Started Club")
    reservation = _seed_reservation(
        seat_id=structure["seat_id"],
        user_id=user.id,
        start_at=datetime.now(timezone.utc) + timedelta(hours=1),
        end_at=datetime.now(timezone.utc) + timedelta(hours=2),
        status=ReservationStatus.SESSION_STARTED.value,
    )

    response = client.patch(f"/api/v1/reservations/{reservation.id}/cancel", headers=headers)

    assert response.status_code == 409
    assert response.json()["detail"] == "Reservation has already started a session"


def test_starting_session_twice_returns_predictable_conflict() -> None:
    structure = _seed_structure("Double Start Club")
    visitor, _ = create_user_with_token(role=UserRole.USER.value, email="double-start-user@example.com")
    admin_headers = _staff_headers_for_structure(structure, "double-start-admin@example.com")
    reservation = _seed_reservation(
        seat_id=structure["seat_id"],
        user_id=visitor.id,
        start_at=datetime.now(timezone.utc) - timedelta(minutes=5),
        end_at=datetime.now(timezone.utc) + timedelta(hours=1),
    )

    first = client.post(f"/api/v1/operations/reservations/{reservation.id}/start-session", headers=admin_headers)
    second = client.post(f"/api/v1/operations/reservations/{reservation.id}/start-session", headers=admin_headers)

    assert first.status_code == 200
    assert second.status_code == 409
    assert second.json()["detail"] == "Session already exists"


def test_finishing_session_completes_reservation_and_keeps_future_reservation_reserved() -> None:
    structure = _seed_structure("Finish Sync Club")
    visitor, _ = create_user_with_token(role=UserRole.USER.value, email="finish-sync-user@example.com")
    admin_headers = _staff_headers_for_structure(structure, "finish-sync-admin@example.com")
    current_reservation = _seed_reservation(
        seat_id=structure["seat_id"],
        user_id=visitor.id,
        start_at=datetime.now(timezone.utc) - timedelta(minutes=10),
        end_at=datetime.now(timezone.utc) + timedelta(minutes=30),
    )
    _seed_reservation(
        seat_id=structure["seat_id"],
        user_id=visitor.id,
        start_at=datetime.now(timezone.utc) + timedelta(hours=2),
        end_at=datetime.now(timezone.utc) + timedelta(hours=3),
    )

    start_response = client.post(
        f"/api/v1/operations/reservations/{current_reservation.id}/start-session",
        headers=admin_headers,
    )
    session_id = start_response.json()["id"]

    finish_response = client.patch(f"/api/v1/operations/sessions/{session_id}/finish", headers=admin_headers)

    assert finish_response.status_code == 200
    assert finish_response.json()["status"] == SessionStatus.FINISHED.value

    with SessionLocal() as db:
        reservation = db.get(Reservation, current_reservation.id)
        seat = db.get(Seat, structure["seat_id"])
        assert reservation is not None
        assert seat is not None
        assert reservation.status == ReservationStatus.COMPLETED.value
        assert seat.operational_status == SeatOperationalStatus.RESERVED.value


def test_finishing_non_active_session_returns_consistent_error() -> None:
    structure = _seed_structure("Finish Error Club")
    visitor, _ = create_user_with_token(role=UserRole.USER.value, email="finish-error-user@example.com")
    admin_headers = _staff_headers_for_structure(structure, "finish-error-admin@example.com")
    reservation = _seed_reservation(
        seat_id=structure["seat_id"],
        user_id=visitor.id,
        start_at=datetime.now(timezone.utc) - timedelta(minutes=10),
        end_at=datetime.now(timezone.utc) + timedelta(minutes=30),
        status=ReservationStatus.COMPLETED.value,
    )
    with SessionLocal() as db:
        session = Session(
            reservation_id=reservation.id,
            seat_id=structure["seat_id"],
            user_id=visitor.id,
            started_at=datetime.now(timezone.utc) - timedelta(hours=1),
            planned_end_at=datetime.now(timezone.utc) - timedelta(minutes=10),
            ended_at=datetime.now(timezone.utc) - timedelta(minutes=5),
            status=SessionStatus.FINISHED.value,
        )
        db.add(session)
        db.commit()
        db.refresh(session)
        session_id = session.id

    response = client.patch(f"/api/v1/operations/sessions/{session_id}/finish", headers=admin_headers)

    assert response.status_code == 409
    assert response.json()["detail"] == "Session is not active"


def test_setting_seat_to_maintenance_with_future_reservation_returns_409() -> None:
    structure = _seed_structure("Maintenance Future Club")
    visitor, _ = create_user_with_token(role=UserRole.USER.value, email="maintenance-future-user@example.com")
    admin_headers = _staff_headers_for_structure(structure, "maintenance-future-admin@example.com")
    _seed_reservation(
        seat_id=structure["seat_id"],
        user_id=visitor.id,
        start_at=datetime.now(timezone.utc) + timedelta(hours=2),
        end_at=datetime.now(timezone.utc) + timedelta(hours=3),
    )

    response = client.patch(
        f"/api/v1/operations/seats/{structure['seat_id']}/status",
        json={"operational_status": SeatOperationalStatus.MAINTENANCE.value, "reason": "Replacement"},
        headers=admin_headers,
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "Active reservations prevent seat status change"


def test_manual_reserved_status_change_is_rejected() -> None:
    structure = _seed_structure("Manual Reserved Club")
    admin_headers = _staff_headers_for_structure(structure, "manual-reserved-admin@example.com")

    response = client.patch(
        f"/api/v1/operations/seats/{structure['seat_id']}/status",
        json={"operational_status": SeatOperationalStatus.RESERVED.value, "reason": "Manual override"},
        headers=admin_headers,
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "Seat status is managed by reservation/session lifecycle"
