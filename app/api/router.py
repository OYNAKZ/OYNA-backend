from fastapi import APIRouter

from app.api.routes import auth, branches, clubs, health, reservations, seats, sessions, zones
from app.core.constants import API_V1_PREFIX


api_router = APIRouter(prefix=API_V1_PREFIX)
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(clubs.router, prefix="/clubs", tags=["clubs"])
api_router.include_router(branches.router, prefix="/branches", tags=["branches"])
api_router.include_router(zones.router, prefix="/zones", tags=["zones"])
api_router.include_router(seats.router, prefix="/seats", tags=["seats"])
api_router.include_router(reservations.router, prefix="/reservations", tags=["reservations"])
api_router.include_router(sessions.router, prefix="/sessions", tags=["sessions"])
api_router.include_router(health.router, tags=["Health"])
