from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class SeatStatusHistory(Base, TimestampMixin):
    __tablename__ = "seat_status_history"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    seat_id: Mapped[int] = mapped_column(ForeignKey("seats.id", ondelete="CASCADE"), nullable=False, index=True)
    changed_by_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    from_status: Mapped[str] = mapped_column(String(50), nullable=False)
    to_status: Mapped[str] = mapped_column(String(50), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    seat = relationship("Seat", back_populates="status_history")
    changed_by = relationship("User", back_populates="seat_status_changes")
