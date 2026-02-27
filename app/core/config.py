from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "NeuroBoard Automation"
    VERSION: str = "1.0.0"

    # Telegram
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_WEBHOOK_URL: str = ""
    TELEGRAM_SECRET_TOKEN: str = "your_secret_token_here_change_in_production"

    # Vision API
    VISION_API_URL: str = ""

    # Google Tasks
    GOOGLE_TASKS_ACCESS_TOKEN: str = ""
    GOOGLE_TASKS_REFRESH_TOKEN: str = ""
    GOOGLE_OAUTH_CLIENT_ID: str = ""
    GOOGLE_OAUTH_CLIENT_SECRET: str = ""
    GOOGLE_OAUTH_TOKEN_URL: str = "https://oauth2.googleapis.com/token"
    GOOGLE_TASKLIST_PROYECTOS_ID: str = "@default"
    GOOGLE_TASKLIST_JOKEM_ID: str = "@default"
    GOOGLE_TASKLIST_PERSONALES_ID: str = "@default"
    GOOGLE_TASKLIST_DOMESTICAS_ID: str = "@default"
    PREVIEW_EXPIRATION_MINUTES: int = 60
    ADMIN_API_TOKEN: str = ""
    HTTP_RETRY_ATTEMPTS: int = 3
    HTTP_RETRY_BACKOFF_SECONDS: float = 0.25

    # Database (sqlite:///./data/neuroboard.db by default)
    DATABASE_URL: str = "sqlite:///./data/neuroboard.db"

    model_config = SettingsConfigDict(env_file=".env")

settings = Settings()
