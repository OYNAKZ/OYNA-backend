"""add user club association

Revision ID: 20260325_add_user_club_id
Revises: 20260322_auth_integrity
Create Date: 2026-03-25 00:00:00
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260325_add_user_club_id"
down_revision = "20260322_auth_integrity"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(sa.Column("club_id", sa.Integer(), nullable=True))
        batch_op.create_index(batch_op.f("ix_users_club_id"), ["club_id"], unique=False)
        batch_op.create_foreign_key("fk_users_club_id_clubs", "clubs", ["club_id"], ["id"], ondelete="SET NULL")


def downgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_constraint("fk_users_club_id_clubs", type_="foreignkey")
        batch_op.drop_index(batch_op.f("ix_users_club_id"))
        batch_op.drop_column("club_id")
