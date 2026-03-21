from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from app.schemas.auth import RegisterRequest, RegisterResponse, TokenResponse
from app.services.auth import (
    PasswordPolicyError,
    UserAlreadyExistsError,
    authenticate_user,
    register_user_account,
)

router = APIRouter()


@router.post("/login", response_model=TokenResponse)
def login(form: OAuth2PasswordRequestForm = Depends()) -> TokenResponse:
    return authenticate_user(email=form.username, password=form.password)


@router.post("/register", response_model=RegisterResponse, status_code=201)
def register(payload: RegisterRequest) -> RegisterResponse:
    try:
        return register_user_account(
            email=str(payload.email),
            password=payload.password,
            full_name=payload.full_name,
        )
    except PasswordPolicyError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except UserAlreadyExistsError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="email already registered") from exc
