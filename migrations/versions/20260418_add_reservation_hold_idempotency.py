"""add reservation hold idempotency

Revision ID: 20260418_reservation_holds
Revises: 20260330_club_ops_owner
Create Date: 2026-04-18 12:00:00
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260418_reservation_holds"
down_revision = "20260330_club_ops_owner"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("reservations") as batch_op:
        batch_op.add_column(sa.Column("idempotency_key", sa.String(length=255), nullable=True))
        batch_op.create_index(batch_op.f("ix_reservations_idempotency_key"), ["idempotency_key"], unique=False)
        batch_op.create_unique_constraint(
            "uq_reservations_user_idempotency_key",
            ["user_id", "idempotency_key"],
        )


def downgrade() -> None:
    with op.batch_alter_table("reservations") as batch_op:
        batch_op.drop_constraint("uq_reservations_user_idempotency_key", type_="unique")
        batch_op.drop_index(batch_op.f("ix_reservations_idempotency_key"))
        batch_op.drop_column("idempotency_key")
