from app.core.security import create_access_token
from app.repositories.user import get_by_email
from app.schemas.auth import LoginRequest, TokenResponse


def authenticate_user(payload: LoginRequest) -> TokenResponse:
    user = get_by_email(payload)
    token = create_access_token(subject=user["email"])
    return TokenResponse(access_token=token["sub"])
