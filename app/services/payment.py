from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.constants import PaymentStatus, ReservationStatus, UserRole
from app.models.payment import Payment
from app.models.user import User
from app.repositories.payment import PaymentRepository, PaymentWebhookEventRepository
from app.repositories.reservation import ReservationRepository
from app.schemas.payment import PaymentCreate, PaymentRead
from app.schemas.common import PaginatedResponse
from app.schemas.payment import PaymentListItemRead
from app.services.payment_provider import get_payment_provider
from app.services.policies import ensure_can_operate_reservation
from app.services.reservation import confirm_reservation_hold_for_payment


def _ensure_payment_access(db: Session, payment: Payment, current_user: User) -> None:
    if current_user.role == UserRole.PLATFORM_ADMIN.value:
        return
    if payment.user_id == current_user.id:
        return
    if current_user.role in (UserRole.CLUB_ADMIN.value, UserRole.OWNER.value) and payment.reservation_id is not None:
        reservation = ReservationRepository(db).get_by_id_with_location(payment.reservation_id)
        if reservation is not None:
            ensure_can_operate_reservation(db, current_user, reservation)
            return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Payment is not accessible")


def _normalize_provider_status(status_value: str) -> str:
    normalized = status_value.lower()
    allowed = {item.value for item in PaymentStatus}
    if normalized not in allowed:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Unsupported payment status")
    return normalized


def _resolve_payment_status_transition(current_status: str, incoming_status: str) -> str:
    if current_status == incoming_status:
        return current_status
    if current_status == PaymentStatus.SUCCEEDED.value:
        if incoming_status in (PaymentStatus.REFUNDED.value, PaymentStatus.PARTIALLY_REFUNDED.value):
            return incoming_status
        return current_status
    if current_status == PaymentStatus.PARTIALLY_REFUNDED.value:
        if incoming_status == PaymentStatus.REFUNDED.value:
            return incoming_status
        return current_status
    if current_status == PaymentStatus.REFUNDED.value:
        return current_status
    if current_status in (PaymentStatus.FAILED.value, PaymentStatus.CANCELLED.value):
        if incoming_status == PaymentStatus.SUCCEEDED.value:
            return incoming_status
        return current_status
    return incoming_status


def create_payment_intent(db: Session, payload: PaymentCreate, current_user: User) -> PaymentRead:
    reservation = ReservationRepository(db).get_by_id_with_location(payload.reservation_id)
    if reservation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reservation not found")
    if reservation.user_id != current_user.id and current_user.role != UserRole.PLATFORM_ADMIN.value:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Reservation is not accessible")
    if reservation.status not in (ReservationStatus.PENDING_PAYMENT.value, ReservationStatus.CONFIRMED.value):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Reservation is not eligible for payment")
    if payload.amount_minor <= 0:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="amount_minor must be positive")

    repo = PaymentRepository(db)
    existing = repo.get_by_user_and_idempotency_key(user_id=current_user.id, idempotency_key=payload.idempotency_key)
    if existing is not None:
        if (
            existing.reservation_id != payload.reservation_id
            or existing.amount_minor != payload.amount_minor
            or existing.currency != payload.currency
            or existing.provider != payload.provider
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Idempotency key already used for different payment intent",
            )
        return PaymentRead.model_validate(existing)

    payment = Payment(
        user_id=current_user.id,
        reservation_id=payload.reservation_id,
        provider=payload.provider,
        provider_payment_id=None,
        status=PaymentStatus.CREATED.value,
        amount_minor=payload.amount_minor,
        currency=payload.currency,
        idempotency_key=payload.idempotency_key,
        checkout_url=None,
    )
    try:
        payment = repo.create(payment)
    except IntegrityError:
        db.rollback()
        existing = repo.get_by_user_and_idempotency_key(user_id=current_user.id, idempotency_key=payload.idempotency_key)
        if existing is None:
            raise
        return PaymentRead.model_validate(existing)

    provider = get_payment_provider(payload.provider)
    provider_intent = provider.create_payment(
        payment_id=payment.id,
        amount_minor=payload.amount_minor,
        currency=payload.currency,
        idempotency_key=payload.idempotency_key,
    )
    updated = repo.update(
        payment,
        provider_payment_id=provider_intent.provider_payment_id,
        checkout_url=provider_intent.checkout_url,
        status=_normalize_provider_status(provider_intent.status),
    )
    return PaymentRead.model_validate(updated)


def get_payment(db: Session, payment_id: int, current_user: User) -> PaymentRead:
    payment = PaymentRepository(db).get_by_id(payment_id)
    if payment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")
    _ensure_payment_access(db, payment, current_user)
    return PaymentRead.model_validate(payment)


def list_payments(
    db: Session,
    current_user: User,
    *,
    status_value: str | None,
    page: int,
    page_size: int,
) -> PaginatedResponse[PaymentListItemRead]:
    payments = PaymentRepository(db).list_all()
    visible: list[Payment] = []
    for payment in payments:
        if status_value is not None and payment.status != status_value:
            continue
        try:
            _ensure_payment_access(db, payment, current_user)
        except HTTPException:
            continue
        visible.append(payment)

    start = max(page - 1, 0) * page_size
    items = visible[start : start + page_size]
    return PaginatedResponse[PaymentListItemRead](
        items=[PaymentListItemRead.model_validate(item) for item in items],
        total=len(visible),
        page=page,
        page_size=page_size,
    )


def reconcile_payment(db: Session, payment_id: int, current_user: User) -> PaymentRead:
    payment = PaymentRepository(db).get_by_id(payment_id)
    if payment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")
    _ensure_payment_access(db, payment, current_user)
    if payment.provider_payment_id is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Payment provider session not started")

    provider = get_payment_provider(payment.provider)
    provider_status = provider.fetch_payment_status(provider_payment_id=payment.provider_payment_id)
    updated = _apply_payment_status(db, payment, provider_status)
    return PaymentRead.model_validate(updated)


def process_payment_webhook(db: Session, *, provider_name: str, body: bytes, headers: dict[str, str]) -> PaymentRead:
    provider = get_payment_provider(provider_name)
    event = provider.verify_webhook(body=body, headers=headers)

    webhook_repo = PaymentWebhookEventRepository(db)
    existing_event = webhook_repo.get_by_provider_event_id(provider=provider_name, event_id=event.event_id)
    if existing_event is not None:
        payment = PaymentRepository(db).get_by_id(existing_event.payment_id) if existing_event.payment_id is not None else None
        if payment is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")
        return PaymentRead.model_validate(payment)

    payment = PaymentRepository(db).get_by_provider_payment_id(
        provider=provider_name,
        provider_payment_id=event.provider_payment_id,
    )
    if payment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")

    updated = _apply_payment_status(db, payment, event.status)
    try:
        webhook_repo.create(
            provider=provider_name,
            event_id=event.event_id,
            event_type=event.event_type,
            payment_id=updated.id,
        )
    except IntegrityError:
        db.rollback()
    return PaymentRead.model_validate(updated)


def _apply_payment_status(db: Session, payment: Payment, provider_status: str) -> Payment:
    normalized_status = _normalize_provider_status(provider_status)
    next_status = _resolve_payment_status_transition(payment.status, normalized_status)
    if next_status != payment.status:
        payment = PaymentRepository(db).update(payment, status=next_status)

    if next_status == PaymentStatus.SUCCEEDED.value and payment.reservation_id is not None:
        reservation = ReservationRepository(db).get_by_id(payment.reservation_id)
        if reservation is not None and reservation.status == ReservationStatus.PENDING_PAYMENT.value:
            try:
                confirm_reservation_hold_for_payment(db, reservation_id=reservation.id)
            except HTTPException:
                pass
    return payment
