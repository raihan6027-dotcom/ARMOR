"""Intent AI: classify what a prompt wants to do with the person in the media.

Loads the model chosen by ml/intent/select_model.py from
<MODEL_DIR>/intent/active.json:

* kind "sklearn": TF-IDF + Logistic Regression pipeline (joblib), the offline default;
* kind "transformers": fine-tuned IndoBERT (needs torch + transformers).

A top probability below the model's threshold becomes UNCERTAIN, which the
policy engine treats as REVIEW. When no model can be loaded, a documented
keyword fallback is used (app.schema.common.normalize_intent) with a low
confidence, so the system keeps failing safe. Every result carries the
model_version that produced it, for the decision log (CLAUDE.md bagian 8).

Model files are local artifacts produced by our own training scripts; joblib
(pickle) must never be pointed at a file from an untrusted source.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from app.core.config import settings
from app.core.logging import get_logger
from app.schema.common import Intent, normalize_intent

logger = get_logger("intent_ai")

FALLBACK_VERSION = "intent-keyword-fallback-v1"
FALLBACK_CONFIDENCE = 0.4


class IntentAI:
    def __init__(self) -> None:
        self._tried = False
        self._predict = None  # callable(prompt) -> (label, confidence)
        self.model_version = FALLBACK_VERSION
        self.threshold = 0.5
        self.load_error: Optional[str] = None

    def reset(self) -> None:
        self.__init__()

    @property
    def model_dir(self) -> Path:
        return Path(settings.model_root) / "intent"

    def _load_sklearn(self, path: Path):
        import joblib

        pipe = joblib.load(path)  # noqa: S301 - local artifact from ml/intent

        def predict(prompt: str) -> tuple[str, float]:
            proba = pipe.predict_proba([prompt])[0]
            i = int(proba.argmax())
            return str(pipe.classes_[i]), float(proba[i])

        return predict

    def _load_transformers(self, path: Path):
        import torch
        from transformers import AutoModelForSequenceClassification, AutoTokenizer

        tok = AutoTokenizer.from_pretrained(path)
        model = AutoModelForSequenceClassification.from_pretrained(path).eval()

        @torch.no_grad()
        def predict(prompt: str) -> tuple[str, float]:
            enc = tok([prompt], truncation=True, max_length=96, return_tensors="pt")
            proba = torch.softmax(model(**enc).logits, dim=-1)[0]
            i = int(proba.argmax())
            return model.config.id2label[i], float(proba[i])

        return predict

    def _ensure_loaded(self) -> None:
        if self._tried:
            return
        self._tried = True
        meta_path = self.model_dir / "active.json"
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            target = self.model_dir / meta["file"]
            if meta["kind"] == "sklearn":
                self._predict = self._load_sklearn(target)
            elif meta["kind"] == "transformers":
                self._predict = self._load_transformers(target)
            else:
                raise ValueError(f"unknown model kind {meta['kind']!r}")
            self.model_version = meta["model_version"]
            self.threshold = float(meta["threshold"])
            logger.info("Intent model loaded: %s", self.model_version)
        except Exception as exc:  # noqa: BLE001 - any failure means "use the fallback"
            self._predict = None
            self.model_version = FALLBACK_VERSION
            self.load_error = f"{type(exc).__name__}: {exc}"
            logger.warning("Intent model unavailable, using keyword fallback (%s)", self.load_error)

    @property
    def model_loaded(self) -> bool:
        self._ensure_loaded()
        return self._predict is not None

    def classify(self, prompt: str) -> dict:
        """{intent, confidence, available, model_version}. `available` is False on
        the keyword fallback."""
        self._ensure_loaded()
        if self._predict is not None:
            try:
                label, confidence = self._predict(prompt)
                intent = normalize_intent(label)
                if confidence < self.threshold:
                    intent = Intent.UNCERTAIN
                return {
                    "intent": intent.value,
                    "confidence": round(confidence, 4),
                    "available": True,
                    "model_version": self.model_version,
                }
            except Exception as exc:  # noqa: BLE001
                logger.warning("Intent model failed at inference: %s", type(exc).__name__)
        intent = normalize_intent(prompt)
        return {
            "intent": intent.value,
            "confidence": FALLBACK_CONFIDENCE if intent is not Intent.UNCERTAIN else 0.2,
            "available": False,
            "model_version": FALLBACK_VERSION,
        }


intent_ai = IntentAI()
