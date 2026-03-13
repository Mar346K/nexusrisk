from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # Required Secrets (No default values allowed. App crashes if missing)
    stripe_secret_key: str
    stripe_webhook_secret: str
    admin_secret: str
    gmail_app_password: str
    redis_url: str = "redis://localhost:6379/0"
    
    # Optional / Configurable
    ollama_model: str = "llama3.1:latest"
    test_user_key: str = "nxr_test_user_001"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

# Instantiate immediately so it validates on boot
settings = Settings()