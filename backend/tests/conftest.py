"""Test fixtures. Configures an isolated SQLite DB and a Gemini-less environment
(so the deterministic fallback path is exercised) BEFORE the app is imported."""
import os
import tempfile

# --- Environment must be set before importing anything from `app` ---
_TMP_DB = os.path.join(tempfile.gettempdir(), "armor_test.db")
_TMP_MODEL_DIR = tempfile.mkdtemp(prefix="armor_models_")

os.environ["DATABASE_URL"] = f"sqlite:///{_TMP_DB}"
os.environ["GEMINI_API_KEY"] = ""              # force deterministic fallback
os.environ["JWT_SECRET"] = "test-secret"
os.environ["MODEL_DIR"] = _TMP_MODEL_DIR       # empty => face model/registry unavailable

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.db.database import Base, engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(autouse=True)
def _fresh_db():
    """Recreate all tables before each test for isolation."""
    import app.models  # noqa: F401  (register models on Base.metadata)

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def auth(client):
    """Register + log in a user; return (headers, user_id)."""
    email = "owner@example.com"
    password = "secret123"
    client.post("/auth/register", json={"email": email, "password": password})
    resp = client.post("/auth/login", json={"email": email, "password": password})
    body = resp.json()
    headers = {"Authorization": f"Bearer {body['access_token']}"}
    return headers, body["user_id"]
