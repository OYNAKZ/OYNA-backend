from enum import Enum

API_V1_PREFIX = "/api/v1"
DEFAULT_PAGE_SIZE = 20


class UserRole(str, Enum):
    USER = "user"
    CLUB_ADMIN = "club_admin"
    OWNER = "owner"
    PLATFORM_ADMIN = "platform_admin"


STAFF_ROLES = (UserRole.CLUB_ADMIN.value, UserRole.OWNER.value, UserRole.PLATFORM_ADMIN.value)
ADMIN_ROLES = (UserRole.OWNER.value, UserRole.PLATFORM_ADMIN.value)


class ReservationStatus(str, Enum):
    CREATED = "created"
    CONFIRMED = "confirmed"
    CHECKED_IN = "checked_in"
    SESSION_STARTED = "session_started"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    NO_SHOW = "no_show"
    COMPLETED = "completed"


ACTIVE_RESERVATION_STATUSES = (
    ReservationStatus.CREATED.value,
    ReservationStatus.CONFIRMED.value,
    ReservationStatus.CHECKED_IN.value,
    ReservationStatus.SESSION_STARTED.value,
)


TERMINAL_RESERVATION_STATUSES = (
    ReservationStatus.CANCELLED.value,
    ReservationStatus.EXPIRED.value,
    ReservationStatus.NO_SHOW.value,
    ReservationStatus.COMPLETED.value,
)


class SessionStatus(str, Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    FINISHED = "finished"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class SeatOperationalStatus(str, Enum):
    AVAILABLE = "available"
    RESERVED = "reserved"
    OCCUPIED = "occupied"
    MAINTENANCE = "maintenance"
    OFFLINE = "offline"


class ScopeRole(str, Enum):
    OWNER = "owner"
    CLUB_ADMIN = "club_admin"
