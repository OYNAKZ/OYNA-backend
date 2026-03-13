from dataclasses import dataclass


@dataclass
class Session:
    id: int
    reservation_id: int
    started_at: str
    ended_at: str | None = None
