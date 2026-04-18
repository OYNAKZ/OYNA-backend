"""add payments tables

Revision ID: 20260418_payments
Revises: 20260418_reservation_holds
Create Date: 2026-04-18 18:00:00
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260418_payments"
down_revision = "20260418_reservation_holds"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "payments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("reservation_id", sa.Integer(), nullable=True),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("provider_payment_id", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("amount_minor", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(length=16), nullable=False),
        sa.Column("idempotency_key", sa.String(length=255), nullable=False),
        sa.Column("checkout_url", sa.String(length=2048), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["reservation_id"], ["reservations.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider", "provider_payment_id", name="uq_payments_provider_payment_id"),
        sa.UniqueConstraint("user_id", "idempotency_key", name="uq_payments_user_idempotency_key"),
    )
    op.create_index(op.f("ix_payments_id"), "payments", ["id"], unique=False)
    op.create_index(op.f("ix_payments_user_id"), "payments", ["user_id"], unique=False)
    op.create_index(op.f("ix_payments_reservation_id"), "payments", ["reservation_id"], unique=False)
    op.create_index(op.f("ix_payments_provider"), "payments", ["provider"], unique=False)
    op.create_index(op.f("ix_payments_provider_payment_id"), "payments", ["provider_payment_id"], unique=False)
    op.create_index(op.f("ix_payments_status"), "payments", ["status"], unique=False)
    op.create_index(op.f("ix_payments_idempotency_key"), "payments", ["idempotency_key"], unique=False)

    op.create_table(
        "payment_webhook_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("payment_id", sa.Integer(), nullable=True),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("event_id", sa.String(length=255), nullable=False),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["payment_id"], ["payments.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider", "event_id", name="uq_payment_webhook_provider_event"),
    )
    op.create_index(op.f("ix_payment_webhook_events_id"), "payment_webhook_events", ["id"], unique=False)
    op.create_index(op.f("ix_payment_webhook_events_payment_id"), "payment_webhook_events", ["payment_id"], unique=False)
    op.create_index(op.f("ix_payment_webhook_events_provider"), "payment_webhook_events", ["provider"], unique=False)
    op.create_index(op.f("ix_payment_webhook_events_event_id"), "payment_webhook_events", ["event_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_payment_webhook_events_event_id"), table_name="payment_webhook_events")
    op.drop_index(op.f("ix_payment_webhook_events_provider"), table_name="payment_webhook_events")
    op.drop_index(op.f("ix_payment_webhook_events_payment_id"), table_name="payment_webhook_events")
    op.drop_index(op.f("ix_payment_webhook_events_id"), table_name="payment_webhook_events")
    op.drop_table("payment_webhook_events")

    op.drop_index(op.f("ix_payments_idempotency_key"), table_name="payments")
    op.drop_index(op.f("ix_payments_status"), table_name="payments")
    op.drop_index(op.f("ix_payments_provider_payment_id"), table_name="payments")
    op.drop_index(op.f("ix_payments_provider"), table_name="payments")
    op.drop_index(op.f("ix_payments_reservation_id"), table_name="payments")
    op.drop_index(op.f("ix_payments_user_id"), table_name="payments")
    op.drop_index(op.f("ix_payments_id"), table_name="payments")
    op.drop_table("payments")
