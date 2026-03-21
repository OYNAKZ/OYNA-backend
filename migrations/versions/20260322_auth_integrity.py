"""harden user auth and integrity

Revision ID: 20260322_auth_integrity
Revises: d3106be2bdb8
Create Date: 2026-03-22 02:20:00
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260322_auth_integrity"
down_revision = "d3106be2bdb8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == "postgresql":
        op.execute("CREATE EXTENSION IF NOT EXISTS citext")
        op.execute("ALTER TABLE users ALTER COLUMN email TYPE citext")

    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column("full_name", existing_type=sa.String(length=255), nullable=True)
        batch_op.alter_column("phone", existing_type=sa.String(length=50), nullable=True)
        batch_op.alter_column(
            "password_hash",
            existing_type=sa.String(length=255),
            type_=sa.Text(),
            nullable=False,
        )
        batch_op.add_column(
            sa.Column(
                "is_email_verified",
                sa.Boolean(),
                server_default=sa.text("false"),
                nullable=False,
            )
        )
        batch_op.add_column(sa.Column("email_verified_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("email_verified_at")
        batch_op.drop_column("is_email_verified")
        batch_op.alter_column(
            "password_hash",
            existing_type=sa.Text(),
            type_=sa.String(length=255),
            nullable=False,
        )
        batch_op.alter_column("phone", existing_type=sa.String(length=50), nullable=False)
        batch_op.alter_column("full_name", existing_type=sa.String(length=255), nullable=False)

    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("ALTER TABLE users ALTER COLUMN email TYPE varchar(255)")
