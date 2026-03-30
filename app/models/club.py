from sqlalchemy import Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class Club(Base, TimestampMixin):
    __tablename__ = "clubs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    branches = relationship("Branch", back_populates="club")
    users = relationship("User", back_populates="club", passive_deletes=True)
    staff_assignments = relationship("StaffAssignment", back_populates="club", passive_deletes=True)
