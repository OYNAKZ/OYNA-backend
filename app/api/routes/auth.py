from fastapi import APIRouter, HTTPException, Request, status

from app.schemas.auth import LoginRequest, RegisterRequest, RegisterResponse, TokenResponse
from app.services.auth import (
    PasswordPolicyError,
    UserAlreadyExistsError,
    authenticate_user,
    register_user_account,
)

router = APIRouter()


@router.post("/login", response_model=TokenResponse)
async def login(request: Request) -> TokenResponse:
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        payload = LoginRequest.model_validate(await request.json())
        return authenticate_user(email=str(payload.email), password=payload.password)

    form = await request.form()
    username = form.get("username")
    password = form.get("password")
    if not isinstance(username, str) or not isinstance(password, str):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Missing login credentials")
    return authenticate_user(email=username, password=password)


@router.post("/register", response_model=RegisterResponse, status_code=201)
def register(payload: RegisterRequest) -> RegisterResponse:
    try:
        return register_user_account(
            email=str(payload.email),
            password=payload.password,
            full_name=payload.full_name,
            phone=payload.phone,
        )
    except PasswordPolicyError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except UserAlreadyExistsError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="email or phone already registered") from exc
