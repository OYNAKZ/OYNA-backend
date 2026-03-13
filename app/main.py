from fastapi import FastAPI

from app.api.router import api_router
from app.core.config import settings


app = FastAPI(title=settings.app_name, version=settings.app_version)
app.include_router(api_router)


@app.get("/", tags=["root"])
def read_root() -> dict[str, str]:
    return {"message": f"{settings.app_name} is running"}
