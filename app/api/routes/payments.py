from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.db import get_db
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.payment import PaymentCreate, PaymentListItemRead, PaymentRead
from app.services.payment import create_payment_intent, get_payment, list_payments, process_payment_webhook, reconcile_payment

router = APIRouter()
webhook_router = APIRouter()


@router.post("", response_model=PaymentRead)
def post_payment(
    payload: PaymentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PaymentRead:
    return create_payment_intent(db, payload, current_user)


@router.get("", response_model=PaginatedResponse[PaymentListItemRead])
def get_payments(
    status_value: str | None = None,
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PaginatedResponse[PaymentListItemRead]:
    return list_payments(
        db,
        current_user,
        status_value=status_value,
        page=page,
        page_size=page_size,
    )


@router.get("/{payment_id}", response_model=PaymentRead)
def get_payment_by_id(
    payment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PaymentRead:
    return get_payment(db, payment_id, current_user)


@router.post("/{payment_id}/reconcile", response_model=PaymentRead)
def post_payment_reconcile(
    payment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PaymentRead:
    return reconcile_payment(db, payment_id, current_user)


@webhook_router.post("/webhooks/{provider}", response_model=PaymentRead)
async def post_payment_webhook(
    provider: str,
    request: Request,
    db: Session = Depends(get_db),
) -> PaymentRead:
    body = await request.body()
    headers = {key: value for key, value in request.headers.items()}
    return process_payment_webhook(db, provider_name=provider, body=body, headers=headers)
