"""Facade over the AI backends used by the intent/risk endpoints.

Intent comes from the local Intent AI (app/ai/intent.py). Risk still uses the
legacy text-only path until Fase 5 replaces it with the local Risk AI; without a
Gemini key (the default) it uses a conservative per-intent table.
"""

from __future__ import annotations

from typing import Optional

from app.ai.gemini_client import gemini_client
from app.ai.intent import intent_ai
from app.schema.common import (
    Intent,
    RiskLevel,
    normalize_intent,
    normalize_risk,
    risk_score_to_level,
)

# Baseline risk per intent when no trained Risk AI is available (Fase 5 replaces
# this with a model). Consent and permission are deliberately NOT inputs: they are
# handled by the policy engine (CLAUDE.md bagian 8).
_FALLBACK_INTENT_RISK: dict[Intent, RiskLevel] = {
    Intent.PERSONAL_CREATION: RiskLevel.LOW,
    Intent.PERSONAL_EDITING: RiskLevel.LOW,
    Intent.SATIRE_PARODY: RiskLevel.LOW,
    Intent.COMMERCIAL_USE: RiskLevel.MEDIUM,
    Intent.POLITICAL_USE: RiskLevel.MEDIUM,
    Intent.IMPERSONATION: RiskLevel.CRITICAL,
    Intent.DEFAMATION: RiskLevel.CRITICAL,
    Intent.SEXUAL_EXPLICIT: RiskLevel.CRITICAL,
    Intent.DECEPTIVE: RiskLevel.HIGH,
    Intent.UNCERTAIN: RiskLevel.MEDIUM,
}

_LEVEL_SCORE = {
    RiskLevel.LOW: 20,
    RiskLevel.MEDIUM: 50,
    RiskLevel.HIGH: 80,
    RiskLevel.CRITICAL: 95,
}


class AIClient:
    def __init__(self) -> None:
        self.gemini = gemini_client

    # -- Intent -------------------------------------------------------------
    def analyze_intent(self, prompt: str) -> dict:
        """Local Intent AI (Fase 4). No third-party AI is called for intent."""
        return intent_ai.classify(prompt)

    # -- Risk ---------------------------------------------------------------
    def analyze_risk(
        self,
        identity_target: str,
        intent: str,
        prompt: Optional[str] = None,
    ) -> dict:
        # Prefer a fresh holistic Gemini read when we have prompt/image context.
        if prompt:
            data = self.gemini.analyze(prompt)
            if data.get("available"):
                level = normalize_risk(data.get("risk")) or risk_score_to_level(
                    data.get("risk_score")
                )
                if level is not None:
                    score = data.get("risk_score")
                    try:
                        score = int(score)
                    except (TypeError, ValueError):
                        score = _LEVEL_SCORE[level]
                    return {
                        "risk_level": level.value,
                        "risk_score": score,
                        "available": True,
                        "model_version": "risk-gemini-legacy",
                    }
        # Deterministic conservative fallback.
        level = self._fallback_level(intent)
        return {
            "risk_level": level.value,
            "risk_score": _LEVEL_SCORE[level],
            "available": False,
            "model_version": "risk-fallback-table-v1",
        }

    @staticmethod
    def _fallback_level(intent: str) -> RiskLevel:
        return _FALLBACK_INTENT_RISK.get(normalize_intent(intent), RiskLevel.HIGH)
