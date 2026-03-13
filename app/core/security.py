from datetime import datetime, timedelta, timezone

from app.core.config import settings


def create_access_token(subject: str, expires_minutes: int | None = None) -> dict[str, str]:
    expires_in = expires_minutes or settings.access_token_expire_minutes
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=expires_in)
    return {"sub": subject, "exp": expires_at.isoformat()}
