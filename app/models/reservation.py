from dataclasses import dataclass


@dataclass
class Reservation:
    id: int
    seat_id: int
    user_id: int
    status: str
