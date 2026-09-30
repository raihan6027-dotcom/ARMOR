"""Risk AI: how harmful would this content be? Score 0-100, level, and the three
features that moved the score the most (for ARMOR Explain).

Loads <MODEL_DIR>/risk/active.json written by ml/risk/train.py after training on
labels agreed by two human annotators. A model trained on SYNTHETIC annotations
is never loaded. Without a usable model the documented per-intent fallback table
is used (CLAUDE.md Fase 5 task 5), and `available` is False.

score = sum over levels of P(level) * center(level), so the score reflects the
model's uncertainty; level follows the CLAUDE.md thresholds (LOW <30,
MEDIUM 30-59, HIGH 60-84, CRITICAL >=85).
"""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from typing import Optional

from app.ai.risk_features import NEUTRAL, RiskFeatures, feature_names, vectorize
from app.core.config import settings
from app.core.logging import get_logger
from app.schema.common import Intent, RiskLevel, risk_score_to_level

logger = get_logger("risk_ai")

FALLBACK_VERSION = "risk-fallback-table-v1"
LEVEL_CENTER = {"LOW": 15.0, "MEDIUM": 45.0, "HIGH": 72.0, "CRITICAL": 92.0}

# Documented fallback: baseline risk per intent (content only, no consent).
FALLBACK_INTENT_RISK: dict[str, RiskLevel] = {
    Intent.PERSONAL_CREATION.value: RiskLevel.LOW,
    Intent.PERSONAL_EDITING.value: RiskLevel.LOW,
    Intent.SATIRE_PARODY.value: RiskLevel.LOW,
    Intent.COMMERCIAL_USE.value: RiskLevel.MEDIUM,
    Intent.POLITICAL_USE.value: RiskLevel.MEDIUM,
    Intent.IMPERSONATION.value: RiskLevel.CRITICAL,
    Intent.DEFAMATION.value: RiskLevel.CRITICAL,
    Intent.SEXUAL_EXPLICIT.value: RiskLevel.CRITICAL,
    Intent.DECEPTIVE.value: RiskLevel.HIGH,
    Intent.UNCERTAIN.value: RiskLevel.MEDIUM,
}
_FALLBACK_SCORE = {
    RiskLevel.LOW: 20,
    RiskLevel.MEDIUM: 50,
    RiskLevel.HIGH: 80,
    RiskLevel.CRITICAL: 95,
}

_GROUPS = (
    "intent",
    "confidence",
    "target_type",
    "media",
    "realism",
    "manipulation",
    "sensitive_context",
    "synthetic_voice",
)


class RiskAI:
    def __init__(self) -> None:
        self._tried = False
        self._model = None
        self._classes: list[str] = []
        self.model_version = FALLBACK_VERSION
        self.load_error: Optional[str] = None

    def reset(self) -> None:
        self.__init__()

    @property
    def model_dir(self) -> Path:
        return Path(settings.model_root) / "risk"

    def _ensure_loaded(self) -> None:
        if self._tried:
            return
        self._tried = True
        try:
            meta = json.loads((self.model_dir / "active.json").read_text(encoding="utf-8"))
            if meta.get("synthetic", True):
                raise ValueError("refusing a model trained on synthetic annotations")
            if meta.get("feature_names") != feature_names():
                raise ValueError("feature layout differs from app/ai/risk_features.py")
            import joblib

            self._model = joblib.load(self.model_dir / meta["file"])  # noqa: S301 - local artifact
            self._classes = [str(c) for c in self._model.classes_]
            self.model_version = meta["model_version"]
            logger.info("Risk model loaded: %s", self.model_version)
        except Exception as exc:  # noqa: BLE001 - any failure means "use the fallback"
            self._model = None
            self.model_version = FALLBACK_VERSION
            self.load_error = f"{type(exc).__name__}: {exc}"
            logger.info("Risk model unavailable, using fallback table (%s)", self.load_error)

    @property
    def model_loaded(self) -> bool:
        self._ensure_loaded()
        return self._model is not None

    def _score(self, f: RiskFeatures) -> float:
        proba = self._model.predict_proba([vectorize(f)])[0]
        return float(sum(p * LEVEL_CENTER[c] for p, c in zip(proba, self._classes, strict=True)))

    def _top_features(self, f: RiskFeatures, score: float) -> list[dict]:
        """Ablation: reset one feature group to a neutral value and see how far the
        score falls. The groups with the largest drop explain the score best."""
        effects = []
        for group in _GROUPS:
            field = group
            neutral = NEUTRAL[group]
            if getattr(f, field) == neutral:
                continue
            delta = score - self._score(replace(f, **{field: neutral}))
            effects.append(
                {"feature": group, "value": getattr(f, field), "effect": round(delta, 1)}
            )
        effects.sort(key=lambda e: e["effect"], reverse=True)
        return effects[:3]

    def assess(self, f: RiskFeatures) -> dict:
        self._ensure_loaded()
        if self._model is not None:
            try:
                score = self._score(f)
                return {
                    "risk_score": int(round(score)),
                    "risk_level": risk_score_to_level(score).value,
                    "available": True,
                    "model_version": self.model_version,
                    "top_features": self._top_features(f, score),
                    "features": f.as_dict(),
                }
            except Exception as exc:  # noqa: BLE001
                logger.warning("Risk model failed at inference: %s", type(exc).__name__)
        level = FALLBACK_INTENT_RISK.get(f.intent, RiskLevel.HIGH)
        return {
            "risk_score": _FALLBACK_SCORE[level],
            "risk_level": level.value,
            "available": False,
            "model_version": FALLBACK_VERSION,
            "top_features": [{"feature": "intent", "value": f.intent, "effect": None}],
            "features": f.as_dict(),
        }


risk_ai = RiskAI()
