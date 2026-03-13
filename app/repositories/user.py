from app.schemas.auth import LoginRequest


def get_by_email(payload: LoginRequest) -> dict[str, str]:
    return {"id": "1", "email": payload.email, "password": payload.password}
