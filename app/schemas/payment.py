from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.core.constants import PaymentProviderName, PaymentStatus
from app.schemas.user import UserRead


class PaymentCreate(BaseModel):
    reservation_id: int
    amount_minor: int
    currency: str = "KZT"
    provider: str = PaymentProviderName.FAKE.value
    idempotency_key: str


class PaymentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    reservation_id: int | None
    provider: str
    provider_payment_id: str | None
    status: str
    amount_minor: int
    currency: str
    idempotency_key: str
    checkout_url: str | None
    created_at: datetime
    updated_at: datetime


class PaymentListItemRead(PaymentRead):
    user: UserRead | None = None


class PaymentWebhookEnvelope(BaseModel):
    event_id: str
    payment_id: str
    status: str
    event_type: str
