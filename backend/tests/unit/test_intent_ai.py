"""Intent AI loader: real sklearn model from a temp dir, threshold, and fallbacks."""

import json

import joblib
import pytest
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

from app.ai.intent import FALLBACK_VERSION, IntentAI
from app.core.config import settings

TRAIN = [
    ("buat avatar kartun saya", "PERSONAL_CREATION"),
    ("ilustrasi anime saya", "PERSONAL_CREATION"),
    ("dia memakai baju tahanan", "DEFAMATION"),
    ("dia diborgol polisi", "DEFAMATION"),
    ("iklan kopi dengan dia", "COMMERCIAL_USE"),
    ("promosi produk dengan dia", "COMMERCIAL_USE"),
]


@pytest.fixture()
def model_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "model_dir", str(tmp_path))
    return tmp_path / "intent"


def _write_model(model_dir, threshold=0.2, kind="sklearn"):
    model_dir.mkdir(parents=True, exist_ok=True)
    pipe = Pipeline([("tfidf", TfidfVectorizer()), ("clf", LogisticRegression(C=50))])
    pipe.fit([t for t, _ in TRAIN], [y for _, y in TRAIN])
    joblib.dump(pipe, model_dir / "m.joblib")
    (model_dir / "active.json").write_text(
        json.dumps(
            {"kind": kind, "file": "m.joblib", "model_version": "test-v1", "threshold": threshold}
        ),
        encoding="utf-8",
    )


def test_loads_active_sklearn_model(model_dir):
    _write_model(model_dir)
    ai = IntentAI()
    out = ai.classify("dia pakai baju tahanan")
    assert out == {**out, "intent": "DEFAMATION", "available": True, "model_version": "test-v1"}
    assert ai.model_loaded


def test_low_confidence_becomes_uncertain(model_dir):
    _write_model(model_dir, threshold=0.99)
    out = IntentAI().classify("dia pakai baju tahanan")
    assert out["intent"] == "UNCERTAIN"
    assert out["available"] is True


def test_missing_model_uses_keyword_fallback(model_dir):
    ai = IntentAI()
    out = ai.classify("buat iklan produk ini")
    assert out == {
        "intent": "COMMERCIAL_USE",
        "confidence": 0.4,
        "available": False,
        "model_version": FALLBACK_VERSION,
    }
    assert ai.load_error
    assert IntentAI().classify("qwerty")["confidence"] == 0.2


def test_unknown_kind_and_missing_transformers_fall_back(model_dir):
    _write_model(model_dir, kind="mystery")
    assert IntentAI().classify("iklan")["model_version"] == FALLBACK_VERSION
    _write_model(model_dir, kind="transformers")  # no torch/transformers in CI
    assert IntentAI().classify("iklan")["available"] is False


def test_inference_error_falls_back(model_dir):
    _write_model(model_dir)
    ai = IntentAI()
    ai._ensure_loaded()
    ai._predict = lambda _p: (_ for _ in ()).throw(RuntimeError("boom"))
    assert ai.classify("iklan produk")["available"] is False


def test_reset_reloads(model_dir):
    ai = IntentAI()
    assert not ai.model_loaded
    _write_model(model_dir)
    ai.reset()
    assert ai.model_loaded
