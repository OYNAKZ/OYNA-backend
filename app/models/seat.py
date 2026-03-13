from dataclasses import dataclass


@dataclass
class Seat:
    id: int
    zone_id: int
    code: str
