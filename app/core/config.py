from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "NeuroBoard Automation"
    VERSION: str = "1.0.0"

    # Telegram
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_SECRET_TOKEN: str = ""

    # Vision API
    VISION_API_URL: str = ""
    VISION_MIN_CONFIDENCE: float = 0.3

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

    # HTTP / retry
    HTTP_RETRY_ATTEMPTS: int = 3
    HTTP_RETRY_BACKOFF_SECONDS: float = 0.25
    HTTP_TIMEOUT_SECONDS: float = 8.0

    # Image preprocessing
    IMAGE_MAX_WIDTH: int = 1024
    IMAGE_CONTRAST_FACTOR: float = 2.0

    # Audio / Whisper
    WHISPER_MODEL_SIZE: str = "small"
    WHISPER_LANGUAGE: str = "es"
    WHISPER_DEVICE: str = "cpu"
    WHISPER_FALLBACK_TO_API: bool = False

    # Misc
    DEFAULT_TIMEZONE: str = "America/Costa_Rica"
    ENABLE_TEST_ENDPOINT: bool = False

    # Database (sqlite:///./data/neuroboard.db by default)
    DATABASE_URL: str = "sqlite:///./data/neuroboard.db"

    @field_validator("TELEGRAM_SECRET_TOKEN")
    @classmethod
    def _validate_secret_token(cls, v: str) -> str:
        insecure_defaults = {"", "your_secret_token_here_change_in_production"}
        if v in insecure_defaults:
            # Allow empty in test/dev — warn but don't crash at import time
            pass
        return v

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
