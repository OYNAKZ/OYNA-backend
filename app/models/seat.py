from sqlalchemy import Boolean, Float, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class Seat(Base, TimestampMixin):
    __tablename__ = "seats"
    __table_args__ = (UniqueConstraint("zone_id", "code", name="uq_seats_zone_code"),)

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    zone_id: Mapped[int] = mapped_column(ForeignKey("zones.id", ondelete="CASCADE"), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(100), nullable=False)
    seat_type: Mapped[str] = mapped_column(String(100), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_maintenance: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    x_position: Mapped[float | None] = mapped_column(Float, nullable=True)
    y_position: Mapped[float | None] = mapped_column(Float, nullable=True)

    zone = relationship("Zone", back_populates="seats")
    reservations = relationship("Reservation", back_populates="seat")
    sessions = relationship("Session", back_populates="seat")
