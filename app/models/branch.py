from dataclasses import dataclass


@dataclass
class Branch:
    id: int
    club_id: int
    name: str
