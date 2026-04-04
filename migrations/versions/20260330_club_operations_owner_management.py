"""club operations and owner management

Revision ID: 20260330_club_ops_owner
Revises: 20260325_add_user_club_id
Create Date: 2026-03-30 23:59:00
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260330_club_ops_owner"
down_revision = "20260325_add_user_club_id"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("seats") as batch_op:
        batch_op.add_column(sa.Column("operational_status", sa.String(length=50), nullable=True))
        batch_op.create_index(batch_op.f("ix_seats_operational_status"), ["operational_status"], unique=False)

    op.execute("UPDATE seats SET operational_status = 'maintenance' WHERE is_maintenance IS TRUE")
    op.execute("UPDATE seats SET operational_status = 'available' WHERE operational_status IS NULL")

    with op.batch_alter_table("seats") as batch_op:
        batch_op.alter_column("operational_status", existing_type=sa.String(length=50), nullable=False)

    op.create_table(
        "staff_assignments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("club_id", sa.Integer(), nullable=False),
        sa.Column("branch_id", sa.Integer(), nullable=True),
        sa.Column("role_in_scope", sa.String(length=50), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["club_id"], ["clubs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_staff_assignments_id"), "staff_assignments", ["id"], unique=False)
    op.create_index(op.f("ix_staff_assignments_user_id"), "staff_assignments", ["user_id"], unique=False)
    op.create_index(op.f("ix_staff_assignments_club_id"), "staff_assignments", ["club_id"], unique=False)
    op.create_index(op.f("ix_staff_assignments_branch_id"), "staff_assignments", ["branch_id"], unique=False)
    op.create_index(op.f("ix_staff_assignments_role_in_scope"), "staff_assignments", ["role_in_scope"], unique=False)

    op.create_table(
        "seat_status_history",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("seat_id", sa.Integer(), nullable=False),
        sa.Column("changed_by_user_id", sa.Integer(), nullable=False),
        sa.Column("from_status", sa.String(length=50), nullable=False),
        sa.Column("to_status", sa.String(length=50), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["changed_by_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["seat_id"], ["seats.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_seat_status_history_id"), "seat_status_history", ["id"], unique=False)
    op.create_index(op.f("ix_seat_status_history_seat_id"), "seat_status_history", ["seat_id"], unique=False)
    op.create_index(
        op.f("ix_seat_status_history_changed_by_user_id"),
        "seat_status_history",
        ["changed_by_user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_seat_status_history_changed_by_user_id"), table_name="seat_status_history")
    op.drop_index(op.f("ix_seat_status_history_seat_id"), table_name="seat_status_history")
    op.drop_index(op.f("ix_seat_status_history_id"), table_name="seat_status_history")
    op.drop_table("seat_status_history")

    op.drop_index(op.f("ix_staff_assignments_role_in_scope"), table_name="staff_assignments")
    op.drop_index(op.f("ix_staff_assignments_branch_id"), table_name="staff_assignments")
    op.drop_index(op.f("ix_staff_assignments_club_id"), table_name="staff_assignments")
    op.drop_index(op.f("ix_staff_assignments_user_id"), table_name="staff_assignments")
    op.drop_index(op.f("ix_staff_assignments_id"), table_name="staff_assignments")
    op.drop_table("staff_assignments")

    with op.batch_alter_table("seats") as batch_op:
        batch_op.drop_index(batch_op.f("ix_seats_operational_status"))
        batch_op.drop_column("operational_status")
