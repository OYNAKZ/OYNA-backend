from fastapi import APIRouter

from app.schemas.auth import LoginRequest, TokenResponse
from app.services.auth import authenticate_user


router = APIRouter()


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest) -> TokenResponse:
    return authenticate_user(payload)
