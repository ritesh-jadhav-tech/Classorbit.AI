import os
import sys
import tempfile
from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["SECRET_KEY"] = "test-secret"
os.environ["ENVIRONMENT"] = "test"
os.environ["UPLOADS_DIR"] = tempfile.mkdtemp(prefix="classorbit-test-uploads-")

from app.db.base import Base
from app.db.init_db import ensure_default_roles
from app.db.session import SessionLocal, engine
from app.main import app


@pytest.fixture(autouse=True)
def clean_database() -> Generator[None, None, None]:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        ensure_default_roles(db)
    finally:
        db.close()
    yield


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def admin_headers(client: TestClient) -> dict[str, str]:
    response = client.post(
        "/api/auth/bootstrap-admin",
        json={"name": "Admin User", "email": "admin@classorbit.edu", "password": "strong-password"},
    )
    assert response.status_code == 201, response.text
    token = response.json()["token"]["access_token"]
    return {"Authorization": f"Bearer {token}"}
