"""Shared pytest fixtures for NeuroBoard tests.

Provides:
  - ``db_session``: an in-memory SQLite session with all tables created,
    automatically rolled back after each test.
  - ``test_client``: a FastAPI TestClient wired to the same in-memory DB,
    with ENABLE_TEST_ENDPOINT forced to True and a deterministic secret token.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.database import Base, get_db
from app.main import app
from app.core.config import settings


# ─────────────────────────────────────────────────────────────────────────────
# In-memory DB session fixture
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture()
def db_session():
    """Yield a transactional SQLAlchemy session backed by in-memory SQLite.

    All tables are created fresh for each test and torn down afterwards.
    """
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


# ─────────────────────────────────────────────────────────────────────────────
# FastAPI TestClient fixture
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture()
def test_client(db_session):
    """Yield a FastAPI TestClient wired to the shared in-memory DB.

    - ENABLE_TEST_ENDPOINT is forced to True so /webhook/test is reachable.
    - TELEGRAM_SECRET_TOKEN is set to a deterministic value.
    - Settings are restored and dependency overrides cleared after the test.
    """
    original_enable_test = settings.ENABLE_TEST_ENDPOINT
    original_secret_token = settings.TELEGRAM_SECRET_TOKEN

    settings.ENABLE_TEST_ENDPOINT = True
    settings.TELEGRAM_SECRET_TOKEN = "test-secret"

    def override_get_db():
        try:
            yield db_session
        finally:
            pass  # session lifecycle managed by db_session fixture

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    try:
        yield client
    finally:
        settings.ENABLE_TEST_ENDPOINT = original_enable_test
        settings.TELEGRAM_SECRET_TOKEN = original_secret_token
        app.dependency_overrides.clear()
