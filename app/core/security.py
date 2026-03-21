import hashlib
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
from jose import jwt

from app.core.config import settings

ALGORITHM = settings.jwt_algorithm
HASH_SCHEME_PREFIXES = {"bcrypt", "bcrypt_sha256"}


def _prepare_password_secret(password: str) -> str:
    if settings.auth_password_hash_scheme == "bcrypt_sha256":
        return hashlib.sha256(password.encode("utf-8")).hexdigest()
    return password


def hash_password(password: str) -> str:
    scheme = settings.auth_password_hash_scheme
    secret = _prepare_password_secret(password).encode("utf-8")
    hashed = bcrypt.hashpw(secret, bcrypt.gensalt(rounds=settings.auth_bcrypt_rounds)).decode("utf-8")
    return f"{scheme}${hashed}"


def _verify_with_scheme(password: str, hashed: str, scheme: str) -> bool:
    secret = password
    if scheme == "bcrypt_sha256":
        secret = hashlib.sha256(password.encode("utf-8")).hexdigest()
    return bcrypt.checkpw(secret.encode("utf-8"), hashed.encode("utf-8"))


def verify_password(plain: str, hashed: str) -> bool:
    prefix, sep, encoded_hash = hashed.partition("$")
    if sep and prefix in HASH_SCHEME_PREFIXES:
        return _verify_with_scheme(plain, encoded_hash, prefix)

    # Backward compatibility with legacy hashes created before scheme-prefixing.
    for scheme in ("bcrypt_sha256", "bcrypt"):
        if _verify_with_scheme(plain, hashed, scheme):
            return True
    return False


def create_access_token(subject: str, expires_minutes: Optional[int] = None) -> str:
    expires_in = expires_minutes or settings.access_token_expire_minutes
    payload = {
        "sub": subject,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=expires_in),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict:
    return jwt.decode(token, settings.jwt_secret_key, algorithms=[ALGORITHM])
