from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    jwt_secret: str
    resend_api_key: str = ""
    email_from: str = "NoraChat <onboarding@resend.dev>"
    ollama_url: str = "http://localhost:11434"
    access_token_minutes: int = 15
    refresh_token_days: int = 30

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()