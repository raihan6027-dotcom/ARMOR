"""Test fixtures. Configures an isolated SQLite DB, a fresh embedding key, and a
model-free environment BEFORE the app is imported. Every test runs fully offline:
the face model is replaced by the synthetic camera in tests/synthetic.py."""

import os
import sys
import tempfile
from pathlib import Path

from cryptography.fernet import Fernet

# --- Environment must be set before importing anything from `app` ---
_TMP_DB = os.path.join(tempfile.gettempdir(), "armor_test.db")
_TMP_MODEL_DIR = tempfile.mkdtemp(prefix="armor_models_")

os.environ["ARMOR_ENV_FILE"] = ""  # never read a developer backend/.env
os.environ["DATABASE_URL"] = f"sqlite:///{_TMP_DB}"
os.environ["GEMINI_API_KEY"] = ""  # force the local fallback
os.environ["JWT_SECRET"] = "test-secret"
os.environ["MODEL_DIR"] = _TMP_MODEL_DIR  # empty => no real model is ever loaded
os.environ["ARMOR_EMBEDDING_KEY"] = Fernet.generate_key().decode()
os.environ["BCRYPT_ROUNDS"] = "4"  # fast hashing in tests only
os.environ["GENERATOR"] = "mock"
os.environ.pop("GENERATOR_TEST_MODE", None)

# The simulated generator (generator_mock/) runs in-process through a TestClient.
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "generator_mock"))

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.ai.face import face_ai  # noqa: E402
from app.core.ratelimit import limiter  # noqa: E402
from app.db.database import Base, engine  # noqa: E402
from app.generation import set_generator  # noqa: E402
from app.generation.mock_adapter import MockGeneratorAdapter  # noqa: E402
from app.main import app  # noqa: E402
from tests import synthetic  # noqa: E402


@pytest.fixture(autouse=True)
def _fresh_db():
    """Recreate all tables before each test for isolation."""
    import app.models  # noqa: F401  (register models on Base.metadata)

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(autouse=True)
def _synthetic_camera(monkeypatch):
    """Replace the face model with the synthetic camera for every test."""
    monkeypatch.setattr(face_ai, "analyze", synthetic.analyze)


@pytest.fixture(autouse=True)
def _mock_generator():
    """Every test generates through the real generator_mock app, in-process."""
    from armor_generator_mock.service import app as generator_app

    set_generator(
        MockGeneratorAdapter("http://generator", 5, client=TestClient(generator_app))
    )
    yield
    set_generator(None)
    limiter.reset()


@pytest.fixture()
def face_model_down(monkeypatch):
    """Simulate the face model being unavailable."""
    monkeypatch.setattr(face_ai, "analyze", lambda _b: None)


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


@pytest.fixture()
def make_user(client):
    """Factory: register + log in a user by email; returns (headers, user_id)."""

    def _make(email: str, password: str = "secret123"):
        client.post("/auth/register", json={"email": email, "password": password})
        body = client.post("/auth/login", json={"email": email, "password": password}).json()
        return {"Authorization": f"Bearer {body['access_token']}"}, body["user_id"]

    return _make


@pytest.fixture()
def enroll(client):
    """Factory: enroll `person` (synthetic face) for the account in `headers`.
    Returns the identity_id."""

    def _enroll(headers, person: str, **kw) -> str:
        r = client.post(
            "/identity/enroll",
            json={
                "images": synthetic.enroll_images(person, **kw),
                "consent": {"agreed": True, "text_version": "face-v1"},
            },
            headers=headers,
        )
        assert r.status_code == 201, r.text
        return r.json()["identity_id"]

    return _enroll
