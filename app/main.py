from fastapi import FastAPI
from app.core.config import settings
from app.db.database import engine, Base
import app.models.models  # Import to ensure they are registered before create_all
from app.api.router import api_router

# Create tables (For production use Alembic, but Base.metadata.create_all is fine to adhere to lightweight constraints)
Base.metadata.create_all(bind=engine)

app = FastAPI(title=settings.PROJECT_NAME, version=settings.VERSION)

app.include_router(api_router, prefix="/api")

@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "version": settings.VERSION,
        "database_url": settings.DATABASE_URL,
        "preview_expiration_minutes": settings.PREVIEW_EXPIRATION_MINUTES,
    }
