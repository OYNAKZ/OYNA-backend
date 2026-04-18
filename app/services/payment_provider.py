from __future__ import annotations

import json
from dataclasses import dataclass
from itertools import count
from typing import Protocol

from fastapi import HTTPException, status

from app.core.constants import PaymentProviderName, PaymentStatus


@dataclass(slots=True)
class ProviderPaymentIntent:
    provider_payment_id: str
    checkout_url: str
    status: str


@dataclass(slots=True)
class VerifiedWebhookEvent:
    event_id: str
    provider_payment_id: str
    event_type: str
    status: str


class PaymentProvider(Protocol):
    def create_payment(
        self,
        *,
        payment_id: int,
        amount_minor: int,
        currency: str,
        idempotency_key: str,
    ) -> ProviderPaymentIntent: ...

    def verify_webhook(self, *, body: bytes, headers: dict[str, str]) -> VerifiedWebhookEvent: ...

    def fetch_payment_status(self, *, provider_payment_id: str) -> str: ...


class FakePaymentProvider:
    def __init__(self) -> None:
        self._sequence = count(1)
        self._payment_statuses: dict[str, str] = {}

    def create_payment(
        self,
        *,
        payment_id: int,
        amount_minor: int,
        currency: str,
        idempotency_key: str,
    ) -> ProviderPaymentIntent:
        provider_payment_id = f"fake_pay_{next(self._sequence)}"
        self._payment_statuses[provider_payment_id] = PaymentStatus.PENDING.value
        return ProviderPaymentIntent(
            provider_payment_id=provider_payment_id,
            checkout_url=f"https://fake-payments.local/checkout/{provider_payment_id}",
            status=PaymentStatus.PENDING.value,
        )

    def verify_webhook(self, *, body: bytes, headers: dict[str, str]) -> VerifiedWebhookEvent:
        try:
            payload = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid webhook payload") from exc

        required = ("event_id", "payment_id", "event_type", "status")
        if any(key not in payload for key in required):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid webhook payload")
        return VerifiedWebhookEvent(
            event_id=str(payload["event_id"]),
            provider_payment_id=str(payload["payment_id"]),
            event_type=str(payload["event_type"]),
            status=str(payload["status"]),
        )

    def fetch_payment_status(self, *, provider_payment_id: str) -> str:
        status_value = self._payment_statuses.get(provider_payment_id)
        if status_value is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Provider payment not found")
        return status_value

    def set_payment_status(self, *, provider_payment_id: str, status_value: str) -> None:
        self._payment_statuses[provider_payment_id] = status_value


_fake_provider = FakePaymentProvider()


def get_payment_provider(provider_name: str) -> PaymentProvider:
    if provider_name == PaymentProviderName.FAKE.value:
        return _fake_provider
    raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Unsupported payment provider")


def get_fake_payment_provider() -> FakePaymentProvider:
    return _fake_provider
