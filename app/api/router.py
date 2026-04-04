from fastapi import APIRouter, Depends

from app.api.dependencies import get_current_user
from app.api.routes import auth, branches, clubs, health, operations, owner, reservations, seats, sessions, users, zones
from app.core.config import settings

api_router = APIRouter(prefix=settings.api_prefix)
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(health.router, tags=["Health"])

protected = APIRouter(dependencies=[Depends(get_current_user)])
protected.include_router(clubs.router, prefix="/clubs", tags=["clubs"])
protected.include_router(branches.router, prefix="/branches", tags=["branches"])
protected.include_router(zones.router, prefix="/zones", tags=["zones"])
protected.include_router(seats.router, prefix="/seats", tags=["seats"])
protected.include_router(reservations.router, prefix="/reservations", tags=["reservations"])
protected.include_router(sessions.router, prefix="/sessions", tags=["sessions"])
protected.include_router(users.router, prefix="/users", tags=["users"])
protected.include_router(operations.router)
protected.include_router(owner.router)

api_router.include_router(protected)
