from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    jwt_secret: str
    resend_api_key: str = ""
    email_from: str = "NoraChat <onboarding@resend.dev>"
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "qwen3.5:9b"
    access_token_minutes: int = 15
    refresh_token_days: int = 30
    supabase_url: str
    supabase_service_key: str
    supabase_bucket: str = "attachments"
    
    ollama_vision_model: str = ""        # empty = use ollama_model for images too
    ollama_num_ctx: int = 16384          # context window (~20 pages of text)

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()