from fastapi import Depends

from app.core.db import get_db


def get_current_user(db=Depends(get_db)) -> dict[str, str]:
    _ = db
    return {"id": "demo-user", "role": "admin"}
