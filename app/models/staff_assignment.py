from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class StaffAssignment(Base, TimestampMixin):
    __tablename__ = "staff_assignments"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    club_id: Mapped[int] = mapped_column(ForeignKey("clubs.id", ondelete="CASCADE"), nullable=False, index=True)
    branch_id: Mapped[int | None] = mapped_column(
        ForeignKey("branches.id", ondelete="CASCADE"), nullable=True, index=True
    )
    role_in_scope: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    user = relationship("User", back_populates="staff_assignments")
    club = relationship("Club", back_populates="staff_assignments")
    branch = relationship("Branch", back_populates="staff_assignments")
