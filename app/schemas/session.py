from pydantic import BaseModel


class SessionBase(BaseModel):
    reservation_id: int
    started_at: str
    ended_at: str | None = None


class SessionCreate(SessionBase):
    pass


class SessionRead(SessionBase):
    id: int
