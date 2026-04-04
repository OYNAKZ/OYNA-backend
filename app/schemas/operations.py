from datetime import datetime

from pydantic import BaseModel

from app.schemas.branch import BranchSummary
from app.schemas.club import ClubRead
from app.schemas.reservation import ReservationRead
from app.schemas.seat import SeatRead
from app.schemas.session import SessionRead
from app.schemas.zone import ZoneSummary


class ReservationOperationsRead(ReservationRead):
    seat: SeatRead


class SessionOperationsRead(SessionRead):
    seat: SeatRead


class ClubZoneLoadRead(BaseModel):
    zone: ZoneSummary
    total_seats: int
    occupied_seats: int
    reserved_seats: int
    maintenance_seats: int
    offline_seats: int
    available_seats: int


class ClubOperationsSummaryRead(BaseModel):
    club_id: int
    branch_id: int | None
    active_sessions: int
    active_reservations: int
    occupied_seats: int
    available_seats: int
    maintenance_seats: int
    offline_seats: int
    zone_load: list[ClubZoneLoadRead]


class OwnerClubOverviewRead(BaseModel):
    club: ClubRead
    branch_count: int
    zone_count: int
    seat_count: int
    active_sessions: int
    active_reservations: int
    current_occupancy_rate: float


class OwnerBranchLoadRead(BaseModel):
    branch: BranchSummary
    occupancy_rate: float


class OwnerAnalyticsRead(BaseModel):
    club_ids: list[int]
    range_start: datetime
    range_end: datetime
    total_reservations: int
    active_reservations: int
    cancellations_count: int
    completed_sessions: int
    active_sessions: int
    club_occupancy_rate: float
    branch_load: list[OwnerBranchLoadRead]
    zone_load: list[ClubZoneLoadRead]
    unavailable_seat_ratio: float
