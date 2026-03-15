from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm

from app.schemas.auth import TokenResponse
from app.schemas.user import UserCreate, UserRead
from app.services.auth import authenticate_user, register_user

router = APIRouter()


@router.post("/login", response_model=TokenResponse)
def login(form: OAuth2PasswordRequestForm = Depends()) -> TokenResponse:
    return authenticate_user(email=form.username, password=form.password)


@router.post("/register", response_model=UserRead, status_code=201)
def register(payload: UserCreate) -> UserRead:
    return register_user(payload)
