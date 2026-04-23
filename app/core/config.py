from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "OYNA Backend"
    app_version: str = "0.1.0"
    app_env: str = "development"
    database_url: str
    jwt_secret_key: str = Field(validation_alias=AliasChoices("JWT_SECRET_KEY", "SECRET_KEY"))
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 30
    api_prefix: str = "/api/v1"
    debug: bool = False
    sqlalchemy_echo: bool = False
    log_level: str = "INFO"
    auth_password_min_len: int = 10
    auth_password_max_len: int = 128
    auth_require_email_verification: bool = False
    auth_anti_enumeration: bool = False
    auth_password_hash_scheme: str = "bcrypt_sha256"
    auth_bcrypt_rounds: int = 12
    reservation_hold_ttl_seconds: int = 900
    payment_provider_default: str = "fake"
    cors_allowed_origins: str = (
        "http://localhost:5173,http://127.0.0.1:5173,http://localhost:8080,http://127.0.0.1:8080"
    )
    dev_seed_admin_email: str | None = None
    dev_seed_admin_password: str | None = None
    dev_seed_admin_full_name: str = "OYNA Local Admin"
    dev_seed_admin_role: str = "platform_admin"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
