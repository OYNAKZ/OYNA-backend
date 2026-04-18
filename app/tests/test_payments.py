from datetime import datetime, time, timedelta, timezone

from fastapi.testclient import TestClient

from app.core.constants import PaymentStatus, ReservationStatus, UserRole
from app.core.db import SessionLocal
from app.main import app
from app.models import Branch, PaymentWebhookEvent, Reservation, Seat, Zone, Club
from app.services.availability import cleanup_expired_holds
from app.services.payment_provider import get_fake_payment_provider
from app.tests.conftest import create_user_with_token

client = TestClient(app)


def _seed_structure(*, club_name: str = "Payment Club", seat_code: str = "A1") -> dict[str, int]:
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


def _create_hold(*, headers: dict[str, str], seat_id: int, key: str = "hold-key") -> int:
    response = client.post(
        "/api/v1/reservations/holds",
        json={
            "seat_id": seat_id,
            "start_at": "2026-04-22T10:00:00Z",
            "end_at": "2026-04-22T12:00:00Z",
            "idempotency_key": key,
        },
        headers=headers,
    )
    assert response.status_code == 200
    return response.json()["id"]


def test_create_payment_intent_links_to_reservation_hold() -> None:
    _, headers = create_user_with_token(role=UserRole.USER.value, email="payment-intent@example.com")
    structure = _seed_structure()
    reservation_id = _create_hold(headers=headers, seat_id=structure["seat_id"])

    response = client.post(
        "/api/v1/payments",
        json={
            "reservation_id": reservation_id,
            "amount_minor": 5000,
            "currency": "KZT",
            "provider": "fake",
            "idempotency_key": "payment-intent-1",
        },
        headers=headers,
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["reservation_id"] == reservation_id
    assert payload["status"] == PaymentStatus.PENDING.value
    assert payload["provider_payment_id"] is not None
    assert payload["checkout_url"] is not None


def test_successful_payment_reconcile_confirms_pending_hold() -> None:
    _, headers = create_user_with_token(role=UserRole.USER.value, email="payment-success@example.com")
    structure = _seed_structure(club_name="Payment Success Club")
    reservation_id = _create_hold(headers=headers, seat_id=structure["seat_id"], key="success-hold")

    payment_response = client.post(
        "/api/v1/payments",
        json={
            "reservation_id": reservation_id,
            "amount_minor": 7000,
            "currency": "KZT",
            "provider": "fake",
            "idempotency_key": "payment-success-intent",
        },
        headers=headers,
    )
    payment = payment_response.json()
    fake_provider = get_fake_payment_provider()
    fake_provider.set_payment_status(
        provider_payment_id=payment["provider_payment_id"],
        status_value=PaymentStatus.SUCCEEDED.value,
    )

    reconcile = client.post(f"/api/v1/payments/{payment['id']}/reconcile", headers=headers)

    assert reconcile.status_code == 200
    assert reconcile.json()["status"] == PaymentStatus.SUCCEEDED.value
    with SessionLocal() as db:
        reservation = db.get(Reservation, reservation_id)
        assert reservation is not None
        assert reservation.status == ReservationStatus.CONFIRMED.value


def test_duplicate_webhook_processing_is_safe() -> None:
    _, headers = create_user_with_token(role=UserRole.USER.value, email="payment-webhook@example.com")
    structure = _seed_structure(club_name="Webhook Club")
    reservation_id = _create_hold(headers=headers, seat_id=structure["seat_id"], key="webhook-hold")
    payment_response = client.post(
        "/api/v1/payments",
        json={
            "reservation_id": reservation_id,
            "amount_minor": 7000,
            "currency": "KZT",
            "provider": "fake",
            "idempotency_key": "payment-webhook-intent",
        },
        headers=headers,
    )
    payment = payment_response.json()
    webhook_payload = {
        "event_id": "evt_duplicate_1",
        "payment_id": payment["provider_payment_id"],
        "event_type": "payment.succeeded",
        "status": "succeeded",
    }

    first = client.post("/api/v1/payments/webhooks/fake", json=webhook_payload)
    second = client.post("/api/v1/payments/webhooks/fake", json=webhook_payload)

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["id"] == second.json()["id"]
    with SessionLocal() as db:
        events = db.query(PaymentWebhookEvent).all()
        reservation = db.get(Reservation, reservation_id)
        assert len(events) == 1
        assert reservation is not None
        assert reservation.status == ReservationStatus.CONFIRMED.value


def test_failed_payment_does_not_confirm_reservation() -> None:
    _, headers = create_user_with_token(role=UserRole.USER.value, email="payment-failed@example.com")
    structure = _seed_structure(club_name="Failed Payment Club")
    reservation_id = _create_hold(headers=headers, seat_id=structure["seat_id"], key="failed-hold")
    payment_response = client.post(
        "/api/v1/payments",
        json={
            "reservation_id": reservation_id,
            "amount_minor": 4000,
            "currency": "KZT",
            "provider": "fake",
            "idempotency_key": "failed-payment-intent",
        },
        headers=headers,
    )
    payment = payment_response.json()

    webhook = client.post(
        "/api/v1/payments/webhooks/fake",
        json={
            "event_id": "evt_failed_1",
            "payment_id": payment["provider_payment_id"],
            "event_type": "payment.failed",
            "status": "failed",
        },
    )

    assert webhook.status_code == 200
    assert webhook.json()["status"] == PaymentStatus.FAILED.value
    with SessionLocal() as db:
        reservation = db.get(Reservation, reservation_id)
        assert reservation is not None
        assert reservation.status == ReservationStatus.PENDING_PAYMENT.value


def test_success_after_hold_expired_does_not_confirm_booking() -> None:
    _, headers = create_user_with_token(role=UserRole.USER.value, email="late-success@example.com")
    structure = _seed_structure(club_name="Late Success Club")
    reservation_id = _create_hold(headers=headers, seat_id=structure["seat_id"], key="late-success-hold")
    payment_response = client.post(
        "/api/v1/payments",
        json={
            "reservation_id": reservation_id,
            "amount_minor": 9000,
            "currency": "KZT",
            "provider": "fake",
            "idempotency_key": "late-success-intent",
        },
        headers=headers,
    )
    payment = payment_response.json()

    with SessionLocal() as db:
        reservation = db.get(Reservation, reservation_id)
        assert reservation is not None
        reservation.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        db.add(reservation)
        db.commit()
        cleanup_expired_holds(db, now=datetime.now(timezone.utc))

    webhook = client.post(
        "/api/v1/payments/webhooks/fake",
        json={
            "event_id": "evt_late_success_1",
            "payment_id": payment["provider_payment_id"],
            "event_type": "payment.succeeded",
            "status": "succeeded",
        },
    )

    assert webhook.status_code == 200
    assert webhook.json()["status"] == PaymentStatus.SUCCEEDED.value
    with SessionLocal() as db:
        reservation = db.get(Reservation, reservation_id)
        assert reservation is not None
        assert reservation.status == ReservationStatus.EXPIRED.value


def test_payment_intent_idempotency_returns_same_payment() -> None:
    _, headers = create_user_with_token(role=UserRole.USER.value, email="payment-idempotent@example.com")
    structure = _seed_structure(club_name="Idempotent Payment Club")
    reservation_id = _create_hold(headers=headers, seat_id=structure["seat_id"], key="idempotent-payment-hold")

    payload = {
        "reservation_id": reservation_id,
        "amount_minor": 6500,
        "currency": "KZT",
        "provider": "fake",
        "idempotency_key": "payment-idempotent-key",
    }
    first = client.post("/api/v1/payments", json=payload, headers=headers)
    second = client.post("/api/v1/payments", json=payload, headers=headers)

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["id"] == second.json()["id"]
