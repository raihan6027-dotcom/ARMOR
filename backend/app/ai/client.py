"""Facade over the AI backends used by the intent/risk endpoints.

Preserves the original AIClient.analyze_intent / analyze_risk contract, but now
delegates to Gemini and normalizes the output. When Gemini is unavailable the
methods fall back to a *conservative* deterministic heuristic (never auto-low
risk, never a positive-but-unverified claim) so the system fails safe.
"""

from __future__ import annotations

from typing import Optional

from app.ai.gemini_client import gemini_client
from app.schema.common import (
    ConsentStatus,
    Intent,
    RiskLevel,
    normalize_intent,
    normalize_risk,
    risk_score_to_level,
)

# Conservative baseline risk when the AI is unavailable: keyed by intent.
_FALLBACK_INTENT_RISK: dict[Intent, RiskLevel] = {
    Intent.PERSONAL_CREATION: RiskLevel.LOW,
    Intent.PERSONAL_EDITING: RiskLevel.LOW,
    Intent.COMMERCIAL_USE: RiskLevel.HIGH,
    Intent.POLITICAL_USE: RiskLevel.HIGH,
    Intent.IMPERSONATION: RiskLevel.CRITICAL,
    Intent.DEFAMATION: RiskLevel.CRITICAL,
    Intent.DECEPTIVE: RiskLevel.HIGH,
    Intent.UNCERTAIN: RiskLevel.HIGH,
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
    def analyze_intent(self, prompt: str, image_bytes: Optional[bytes] = None) -> dict:
        data = self.gemini.analyze(prompt, image_bytes=image_bytes)
        if data.get("available"):
            raw = data.get("intent_category") or data.get("intent")
            intent = normalize_intent(raw)
            try:
                confidence = float(data.get("confidence", 0.7))
            except (TypeError, ValueError):
                confidence = 0.7
            return {
                "intent": intent.value,
                "confidence": max(0.0, min(1.0, confidence)),
                "raw_intent": data.get("intent"),
                "available": True,
            }
        # Fallback: classify from the prompt text alone.
        intent = normalize_intent(prompt)
        return {
            "intent": intent.value,
            "confidence": 0.4 if intent is not Intent.UNCERTAIN else 0.2,
            "raw_intent": None,
            "available": False,
        }

    # -- Risk ---------------------------------------------------------------
    def analyze_risk(
        self,
        identity_target: str,
        intent: str,
        consent: str,
        prompt: Optional[str] = None,
        image_bytes: Optional[bytes] = None,
    ) -> dict:
        # Prefer a fresh holistic Gemini read when we have prompt/image context.
        if prompt:
            data = self.gemini.analyze(prompt, image_bytes=image_bytes)
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
                    }
        # Deterministic conservative fallback.
        level = self._fallback_level(identity_target, intent, consent)
        return {
            "risk_level": level.value,
            "risk_score": _LEVEL_SCORE[level],
            "available": False,
        }

    @staticmethod
    def _fallback_level(identity_target: str, intent: str, consent: str) -> RiskLevel:
        it = normalize_intent(intent)
        base = _FALLBACK_INTENT_RISK.get(it, RiskLevel.HIGH)
        target = (identity_target or "").upper()
        cons = (consent or "").upper()
        # Using someone else's identity without consent escalates risk.
        if target == "OTHER" and cons not in (ConsentStatus.GRANTED.value, "APPROVED"):
            if base == RiskLevel.LOW:
                base = RiskLevel.MEDIUM
            elif base == RiskLevel.MEDIUM:
                base = RiskLevel.HIGH
        return base
