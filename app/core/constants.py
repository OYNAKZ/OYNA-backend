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
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CHECKED_IN = "checked_in"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    NO_SHOW = "no_show"


class SessionStatus(str, Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
