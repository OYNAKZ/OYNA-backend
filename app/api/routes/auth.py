from fastapi import APIRouter

from app.schemas.auth import LoginRequest, TokenResponse
from app.schemas.user import UserCreate, UserRead
from app.services.auth import authenticate_user, register_user

router = APIRouter()


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest) -> TokenResponse:
    return authenticate_user(payload)


@router.post("/register", response_model=UserRead, status_code=201)
def register(payload: UserCreate) -> UserRead:
    return register_user(payload)
