from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Project API"
    app_version: str = "0.1.0"
    database_url: str
    jwt_secret_key: str = Field(validation_alias=AliasChoices("JWT_SECRET_KEY", "SECRET_KEY"))
    access_token_expire_minutes: int = 60
    model_config = SettingsConfigDict(env_file="C:/Users/LEGION/Desktop/OYNA/.env", extra="ignore")


settings = Settings()
