from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.database import Base, get_db
from app.main import app
from app.core.config import settings


def _build_test_client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


def test_admin_previews_requires_token() -> None:
    client = _build_test_client()
    original_admin_token = settings.ADMIN_API_TOKEN
    settings.ADMIN_API_TOKEN = "secret-admin"
    try:
        response = client.get("/api/telegram/previews")
    finally:
        settings.ADMIN_API_TOKEN = original_admin_token
        app.dependency_overrides.clear()

    assert response.status_code == 403


def test_admin_previews_returns_created_preview() -> None:
    client = _build_test_client()
    original_admin_token = settings.ADMIN_API_TOKEN
    original_secret_token = settings.TELEGRAM_SECRET_TOKEN
    settings.ADMIN_API_TOKEN = "secret-admin"
    settings.TELEGRAM_SECRET_TOKEN = "telegram-secret"
    try:
        webhook_response = client.post(
            "/api/telegram/webhook",
            headers={"X-Telegram-Bot-Api-Secret-Token": "telegram-secret"},
            json={"mock_lines": ["-Lavar ropa", "-JP: Rutina gym mañana"]},
        )
        admin_response = client.get(
            "/api/telegram/previews",
            headers={"X-Admin-Api-Token": "secret-admin"},
        )
    finally:
        settings.ADMIN_API_TOKEN = original_admin_token
        settings.TELEGRAM_SECRET_TOKEN = original_secret_token
        app.dependency_overrides.clear()

    assert webhook_response.status_code == 200
    assert webhook_response.json()["preview_id"] is not None
    assert admin_response.status_code == 200
    payload = admin_response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["status"] == "pending"
    assert payload["items"][0]["task_count"] == 2


def test_admin_previews_filters_by_status() -> None:
    client = _build_test_client()
    original_admin_token = settings.ADMIN_API_TOKEN
    original_secret_token = settings.TELEGRAM_SECRET_TOKEN
    settings.ADMIN_API_TOKEN = "secret-admin"
    settings.TELEGRAM_SECRET_TOKEN = "telegram-secret"
    try:
        client.post(
            "/api/telegram/webhook",
            headers={"X-Telegram-Bot-Api-Secret-Token": "telegram-secret"},
            json={"mock_lines": ["-Lavar ropa"]},
        )
        response = client.get(
            "/api/telegram/previews?status=completed",
            headers={"X-Admin-Api-Token": "secret-admin"},
        )
    finally:
        settings.ADMIN_API_TOKEN = original_admin_token
        settings.TELEGRAM_SECRET_TOKEN = original_secret_token
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["status_filter"] == "completed"
    assert payload["total"] == 0
