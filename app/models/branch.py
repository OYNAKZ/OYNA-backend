from datetime import time

from sqlalchemy import Boolean, Float, ForeignKey, String, Time
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class Branch(Base, TimestampMixin):
    __tablename__ = "branches"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    club_id: Mapped[int] = mapped_column(ForeignKey("clubs.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    address: Mapped[str] = mapped_column(String(500), nullable=False)
    city: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    open_time: Mapped[time] = mapped_column(Time, nullable=False)
    close_time: Mapped[time] = mapped_column(Time, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    club = relationship("Club", back_populates="branches")
    zones = relationship("Zone", back_populates="branch")
    staff_assignments = relationship("StaffAssignment", back_populates="branch", passive_deletes=True)
