"""Risk AI loader: weighted score, level, top features, and refusals."""

import json

import joblib
import numpy as np
import pytest
from sklearn.linear_model import LogisticRegression

from app.ai.risk import FALLBACK_VERSION, RiskAI
from app.ai.risk_features import HIGH, LOW, feature_names, from_prompt, vectorize
from app.core.config import settings


def _feat(intent, target="OTHER_UNREGISTERED", prompt="buat gambar"):
    return from_prompt(prompt, intent, 0.9, target, "IMAGE")


@pytest.fixture()
def risk_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "model_dir", str(tmp_path))
    return tmp_path / "risk"


def _train(risk_dir, synthetic=False, names=None):
    risk_dir.mkdir(parents=True, exist_ok=True)
    rows = [
        (_feat("PERSONAL_EDITING", "SELF"), "LOW"),
        (_feat("PERSONAL_CREATION", "SELF"), "LOW"),
        (_feat("COMMERCIAL_USE"), "MEDIUM"),
        (_feat("POLITICAL_USE"), "MEDIUM"),
        (_feat("DECEPTIVE"), "HIGH"),
        (_feat("DECEPTIVE", prompt="video fotorealistik"), "HIGH"),
        (_feat("DEFAMATION", prompt="foto fotorealistik"), "CRITICAL"),
        (_feat("SEXUAL_EXPLICIT"), "CRITICAL"),
    ] * 3
    X = np.array([vectorize(f) for f, _ in rows])
    model = LogisticRegression(C=20, max_iter=2000).fit(X, [y for _, y in rows])
    joblib.dump(model, risk_dir / "risk_model.joblib")
    (risk_dir / "active.json").write_text(
        json.dumps(
            {
                "kind": "sklearn",
                "file": "risk_model.joblib",
                "model_version": "risk-test-v1",
                "synthetic": synthetic,
                "feature_names": names or feature_names(),
            }
        ),
        encoding="utf-8",
    )


def test_model_score_level_and_top_features(risk_dir):
    _train(risk_dir)
    ai = RiskAI()
    out = ai.assess(_feat("DEFAMATION", prompt="foto fotorealistik"))
    assert out["available"] and out["model_version"] == "risk-test-v1"
    assert 0 <= out["risk_score"] <= 100
    assert out["risk_level"] in ("HIGH", "CRITICAL")
    assert out["top_features"][0]["feature"] == "intent"
    assert len(out["top_features"]) <= 3
    low = ai.assess(_feat("PERSONAL_EDITING", "SELF"))
    assert low["risk_score"] < out["risk_score"]
    assert low["risk_level"] == "LOW"


def test_refuses_synthetic_model(risk_dir):
    _train(risk_dir, synthetic=True)
    ai = RiskAI()
    assert ai.assess(_feat("COMMERCIAL_USE"))["model_version"] == FALLBACK_VERSION
    assert "synthetic" in ai.load_error


def test_refuses_mismatched_feature_layout(risk_dir):
    _train(risk_dir, names=["old"])
    ai = RiskAI()
    assert not ai.model_loaded
    assert "feature layout" in ai.load_error


@pytest.mark.parametrize(
    ("intent", "level", "score"),
    [
        ("PERSONAL_EDITING", "LOW", 20),
        ("COMMERCIAL_USE", "MEDIUM", 50),
        ("DECEPTIVE", "HIGH", 80),
        ("DEFAMATION", "CRITICAL", 95),
        ("UNCERTAIN", "MEDIUM", 50),
    ],
)
def test_fallback_table(risk_dir, intent, level, score):
    out = RiskAI().assess(_feat(intent))
    assert (out["risk_level"], out["risk_score"], out["available"]) == (level, score, False)
    assert out["top_features"][0]["feature"] == "intent"


def test_inference_error_falls_back(risk_dir):
    _train(risk_dir)
    ai = RiskAI()
    assert ai.model_loaded
    ai._model = None  # simulate a broken model object after load
    ai._tried = True
    assert ai.assess(_feat("COMMERCIAL_USE"))["available"] is False


def test_features_reported_and_realism_flows(risk_dir):
    out = RiskAI().assess(_feat("SATIRE_PARODY", prompt="karikatur kartun"))
    assert out["features"]["realism"] == LOW
    out = RiskAI().assess(_feat("SATIRE_PARODY", prompt="parodi fotorealistik"))
    assert out["features"]["realism"] == HIGH


def test_reset(risk_dir):
    ai = RiskAI()
    assert not ai.model_loaded
    _train(risk_dir)
    ai.reset()
    assert ai.model_loaded
