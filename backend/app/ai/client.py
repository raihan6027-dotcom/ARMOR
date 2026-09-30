"""Facade over the local AI components used by the gateway and the analysis
endpoints. Everything runs on this machine: no third-party AI API is called
anywhere in the main path (CLAUDE.md bagian 12)."""

from __future__ import annotations

from app.ai.intent import intent_ai
from app.ai.risk import risk_ai
from app.ai.risk_features import RiskFeatures, from_prompt


class AIClient:
    def analyze_intent(self, prompt: str) -> dict:
        return intent_ai.classify(prompt)

    def risk_features(
        self,
        prompt: str,
        intent: str,
        confidence: float,
        target_type: str,
        media: str,
        synthetic_voice: int = 0,
    ) -> RiskFeatures:
        return from_prompt(prompt, intent, confidence, target_type, media, synthetic_voice)

    def analyze_risk(self, features: RiskFeatures) -> dict:
        return risk_ai.assess(features)
