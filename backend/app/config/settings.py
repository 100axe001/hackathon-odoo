"""Application settings, read once from the environment."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://dealflow:dealflow@localhost:5433/dealflow"

    # Signing key for session tokens. The default is fine for local work and is
    # overridden by .env; a real deployment must set it.
    jwt_secret: str = "dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 480

    # Cookie is host-only over plain HTTP in development. Secure must be on in
    # production, which also requires HTTPS.
    cookie_name: str = "dealflow_session"
    cookie_secure: bool = False


settings = Settings()
