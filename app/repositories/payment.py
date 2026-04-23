from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.payment import Payment
from app.models.payment_webhook_event import PaymentWebhookEvent


class PaymentRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, payment_id: int) -> Payment | None:
        return self.db.get(Payment, payment_id)

    def get_by_user_and_idempotency_key(self, *, user_id: int, idempotency_key: str) -> Payment | None:
        stmt = select(Payment).where(
            Payment.user_id == user_id,
            Payment.idempotency_key == idempotency_key,
        )
        return self.db.scalar(stmt)

    def list_all(self) -> list[Payment]:
        stmt = select(Payment).order_by(Payment.created_at.desc(), Payment.id.desc())
        return list(self.db.scalars(stmt))

    def get_by_provider_payment_id(self, *, provider: str, provider_payment_id: str) -> Payment | None:
        stmt = select(Payment).where(
            Payment.provider == provider,
            Payment.provider_payment_id == provider_payment_id,
        )
        return self.db.scalar(stmt)

    def create(self, payment: Payment) -> Payment:
        self.db.add(payment)
        self.db.commit()
        self.db.refresh(payment)
        return payment

    def update(self, payment: Payment, **changes) -> Payment:
        for field, value in changes.items():
            setattr(payment, field, value)
        self.db.add(payment)
        self.db.commit()
        self.db.refresh(payment)
        return payment


class PaymentWebhookEventRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_provider_event_id(self, *, provider: str, event_id: str) -> PaymentWebhookEvent | None:
        stmt = select(PaymentWebhookEvent).where(
            PaymentWebhookEvent.provider == provider,
            PaymentWebhookEvent.event_id == event_id,
        )
        return self.db.scalar(stmt)

    def create(self, *, provider: str, event_id: str, event_type: str, payment_id: int | None) -> PaymentWebhookEvent:
        item = PaymentWebhookEvent(
            provider=provider,
            event_id=event_id,
            event_type=event_type,
            payment_id=payment_id,
        )
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item
