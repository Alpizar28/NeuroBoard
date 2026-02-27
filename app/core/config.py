from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "NeuroBoard Automation"
    VERSION: str = "1.0.0"
    
    # Telegram
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_WEBHOOK_URL: str = ""
    TELEGRAM_SECRET_TOKEN: str = "your_secret_token_here_change_in_production"
    
    # Database (sqlite:///./data/neuroboard.db by default)
    DATABASE_URL: str = "sqlite:///./data/neuroboard.db"

    class Config:
        env_file = ".env"

settings = Settings()
