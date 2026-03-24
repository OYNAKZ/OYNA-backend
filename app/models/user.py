from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.constants import UserRole
from app.models.base import Base, TimestampMixin


class User(Base, TimestampMixin):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("email", name="users_email_key"),
        UniqueConstraint("phone", name="users_phone_key"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    club_id: Mapped[int | None] = mapped_column(ForeignKey("clubs.id", ondelete="SET NULL"), nullable=True, index=True)
    email: Mapped[str] = mapped_column(String(255, collation="NOCASE"), nullable=False, index=True, unique=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True, unique=True)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    role: Mapped[str] = mapped_column(String(50), default=UserRole.USER.value, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_email_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    email_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    reservations = relationship("Reservation", back_populates="user")
    sessions = relationship("Session", back_populates="user")
    club = relationship("Club", back_populates="users")
