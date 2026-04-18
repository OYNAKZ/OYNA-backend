from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.constants import ReservationStatus
from app.models.base import Base, TimestampMixin


class Reservation(Base, TimestampMixin):
    __tablename__ = "reservations"
    __table_args__ = (UniqueConstraint("user_id", "idempotency_key", name="uq_reservations_user_idempotency_key"),)

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    seat_id: Mapped[int] = mapped_column(ForeignKey("seats.id", ondelete="CASCADE"), nullable=False, index=True)
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default=ReservationStatus.CONFIRMED.value, index=True
    )
    idempotency_key: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="reservations")
    seat = relationship("Seat", back_populates="reservations")
    session = relationship("Session", back_populates="reservation", uselist=False)
    payments = relationship("Payment", back_populates="reservation")
