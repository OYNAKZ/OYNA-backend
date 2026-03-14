from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    jwt_secret_key: str
    access_token_expire_minutes: int = 60
    app_name:str
    app_version:str
    model_config = SettingsConfigDict(env_file="C:/Users/LEGION/Desktop/OYNA/.env", extra="ignore")



settings = Settings()
print("DATABASE_URL =", settings.database_url)
print("JWT_SECRET_KEY =", settings.jwt_secret_key)
