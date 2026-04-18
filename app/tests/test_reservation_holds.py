from datetime import datetime, time, timedelta, timezone

from fastapi.testclient import TestClient

from app.core.constants import ReservationStatus, UserRole
from app.core.db import SessionLocal
from app.main import app
from app.models import Branch, Club, Reservation, Seat, Zone
from app.services.availability import check_seat_availability, cleanup_expired_holds
from app.tests.conftest import create_user_with_token

client = TestClient(app)


def _seed_structure(*, club_name: str = "Hold Club", seat_code: str = "A1") -> dict[str, int]:
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
        )
        db.add(seat)
        db.commit()
        db.refresh(seat)
        return {"club_id": club.id, "branch_id": branch.id, "zone_id": zone.id, "seat_id": seat.id}


def test_create_pending_payment_hold() -> None:
    user, headers = create_user_with_token(role=UserRole.USER.value, email="hold-user@example.com")
    structure = _seed_structure()

    response = client.post(
        "/api/v1/reservations/holds",
        json={
            "seat_id": structure["seat_id"],
            "start_at": "2026-04-21T10:00:00Z",
            "end_at": "2026-04-21T12:00:00Z",
            "idempotency_key": "hold-1",
        },
        headers=headers,
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["user_id"] == user.id
    assert payload["status"] == ReservationStatus.PENDING_PAYMENT.value
    assert payload["expires_at"] is not None


def test_pending_payment_hold_blocks_overlapping_reservation() -> None:
    _, hold_headers = create_user_with_token(role=UserRole.USER.value, email="hold-owner@example.com")
    _, other_headers = create_user_with_token(role=UserRole.USER.value, email="other-booker@example.com")
    structure = _seed_structure(club_name="Hold Blocking Club")

    hold = client.post(
        "/api/v1/reservations/holds",
        json={
            "seat_id": structure["seat_id"],
            "start_at": "2026-04-21T10:00:00Z",
            "end_at": "2026-04-21T12:00:00Z",
            "idempotency_key": "hold-block",
        },
        headers=hold_headers,
    )
    reservation = client.post(
        "/api/v1/reservations",
        json={
            "seat_id": structure["seat_id"],
            "start_at": "2026-04-21T11:00:00Z",
            "end_at": "2026-04-21T12:30:00Z",
            "status": "confirmed",
        },
        headers=other_headers,
    )

    assert hold.status_code == 200
    assert reservation.status_code == 409
    assert reservation.json()["detail"] == "Seat already reserved for this time range"


def test_create_hold_is_idempotent_for_same_client_key() -> None:
    _, headers = create_user_with_token(role=UserRole.USER.value, email="idempotent-hold@example.com")
    structure = _seed_structure(club_name="Idempotent Hold Club")

    first = client.post(
        "/api/v1/reservations/holds",
        json={
            "seat_id": structure["seat_id"],
            "start_at": "2026-04-21T10:00:00Z",
            "end_at": "2026-04-21T12:00:00Z",
            "idempotency_key": "same-hold-key",
        },
        headers=headers,
    )
    second = client.post(
        "/api/v1/reservations/holds",
        json={
            "seat_id": structure["seat_id"],
            "start_at": "2026-04-21T10:00:00Z",
            "end_at": "2026-04-21T12:00:00Z",
            "idempotency_key": "same-hold-key",
        },
        headers=headers,
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["id"] == second.json()["id"]


def test_confirm_pending_payment_hold_transitions_to_confirmed() -> None:
    _, headers = create_user_with_token(role=UserRole.USER.value, email="confirm-hold@example.com")
    structure = _seed_structure(club_name="Confirm Hold Club")

    hold_response = client.post(
        "/api/v1/reservations/holds",
        json={
            "seat_id": structure["seat_id"],
            "start_at": "2026-04-21T10:00:00Z",
            "end_at": "2026-04-21T12:00:00Z",
            "idempotency_key": "confirm-key",
        },
        headers=headers,
    )
    reservation_id = hold_response.json()["id"]

    confirm_response = client.patch(f"/api/v1/reservations/{reservation_id}/confirm", headers=headers)

    assert confirm_response.status_code == 200
    assert confirm_response.json()["status"] == ReservationStatus.CONFIRMED.value
    assert confirm_response.json()["expires_at"] is None


def test_expired_hold_no_longer_blocks_availability() -> None:
    user, headers = create_user_with_token(role=UserRole.USER.value, email="expired-hold@example.com")
    structure = _seed_structure(club_name="Expired Hold Club")

    hold_response = client.post(
        "/api/v1/reservations/holds",
        json={
            "seat_id": structure["seat_id"],
            "start_at": "2026-04-21T10:00:00Z",
            "end_at": "2026-04-21T12:00:00Z",
            "idempotency_key": "expire-key",
            "hold_ttl_seconds": 1,
        },
        headers=headers,
    )
    reservation_id = hold_response.json()["id"]

    with SessionLocal() as db:
        hold = db.get(Reservation, reservation_id)
        hold.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        db.add(hold)
        db.commit()
        expired_count = cleanup_expired_holds(db, now=datetime.now(timezone.utc))
        result = check_seat_availability(
            db,
            seat_id=structure["seat_id"],
            start_at=datetime(2026, 4, 21, 10, 0, tzinfo=timezone.utc),
            end_at=datetime(2026, 4, 21, 12, 0, tzinfo=timezone.utc),
        )
        refreshed = db.get(Reservation, reservation_id)

    assert expired_count == 1
    assert refreshed is not None
    assert refreshed.status == ReservationStatus.EXPIRED.value
    assert result.is_available is True


def test_hold_expiration_boundary_does_not_block() -> None:
    user, headers = create_user_with_token(role=UserRole.USER.value, email="boundary-hold@example.com")
    structure = _seed_structure(club_name="Boundary Hold Club")

    hold_response = client.post(
        "/api/v1/reservations/holds",
        json={
            "seat_id": structure["seat_id"],
            "start_at": "2026-04-21T10:00:00Z",
            "end_at": "2026-04-21T12:00:00Z",
            "idempotency_key": "boundary-key",
        },
        headers=headers,
    )
    reservation_id = hold_response.json()["id"]

    with SessionLocal() as db:
        hold = db.get(Reservation, reservation_id)
        boundary_now = datetime.now(timezone.utc)
        hold.expires_at = boundary_now
        db.add(hold)
        db.commit()
        cleanup_expired_holds(db, now=boundary_now)
        result = check_seat_availability(
            db,
            seat_id=structure["seat_id"],
            start_at=datetime(2026, 4, 21, 10, 0, tzinfo=timezone.utc),
            end_at=datetime(2026, 4, 21, 12, 0, tzinfo=timezone.utc),
        )

    assert result.is_available is True


def test_duplicate_hold_request_with_same_key_but_different_payload_returns_409() -> None:
    _, headers = create_user_with_token(role=UserRole.USER.value, email="conflicting-key@example.com")
    structure = _seed_structure(club_name="Conflicting Key Club")

    first = client.post(
        "/api/v1/reservations/holds",
        json={
            "seat_id": structure["seat_id"],
            "start_at": "2026-04-21T10:00:00Z",
            "end_at": "2026-04-21T12:00:00Z",
            "idempotency_key": "conflict-key",
        },
        headers=headers,
    )
    second = client.post(
        "/api/v1/reservations/holds",
        json={
            "seat_id": structure["seat_id"],
            "start_at": "2026-04-21T12:00:00Z",
            "end_at": "2026-04-21T13:00:00Z",
            "idempotency_key": "conflict-key",
        },
        headers=headers,
    )

    assert first.status_code == 200
    assert second.status_code == 409
    assert second.json()["detail"] == "Idempotency key already used for different reservation intent"
