from dataclasses import dataclass


@dataclass
class Zone:
    id: int
    branch_id: int
    name: str
