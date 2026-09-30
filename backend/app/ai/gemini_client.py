"""Gemini-backed analysis client (intent / risk / legal-consent context).

Mirrors the team's Colab pipeline: one multimodal call takes the image + subject
identity + prompt and returns a structured JSON analysis. The model's own
"decision" is captured but treated as ADVISORY only — the deterministic policy
engine produces the authoritative ALLOW/REVIEW/DENY.

If no API key is configured or the call fails, `available` is False and callers
apply a safe fallback (never auto-ALLOW).
"""
from __future__ import annotations

import io
import json
from typing import Any, Optional

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("gemini")

_ANALYSIS_PROMPT = """
You are a senior cyber-law and content-policy analyst for a digital-identity
protection system. Analyze the request below and respond with PURE JSON only
(no markdown fences, no commentary).

Subject identity: "{identity}"
Identity is unknown/unverified: {is_unknown}
User prompt: "{prompt}"

Return exactly these keys:
- "detected_language": source language of the prompt (e.g. "Indonesian", "English").
- "translated_prompt": accurate English translation of the prompt.
- "profession": subject's main field if a public figure, else "Unknown".
- "is_public_figure": "Yes" or "No".
- "intent": the requester's underlying goal in <=5 words.
- "intent_category": ONE of PERSONAL_CREATION, PERSONAL_EDITING, COMMERCIAL_USE,
  IMPERSONATION, DEFAMATION, POLITICAL_USE, DECEPTIVE, UNCERTAIN.
- "consent": <=2 sentence legal note (privacy / defamation / IP). Do NOT use the
  words allow, deny, izin, tolak, or review.
- "risk": ONE of LOW, MEDIUM, HIGH, CRITICAL.
- "risk_score": integer 0-100 matching the risk level.
- "confidence": float 0-1 for the intent classification.
- "decision": ADVISORY only — ALLOW, REVIEW, or DENY.
""".strip()


class GeminiClient:
    def __init__(self) -> None:
        self._client = None
        self._init_error: Optional[str] = None

    @property
    def configured(self) -> bool:
        return bool(settings.gemini_api_key)

    def _get_client(self):
        if self._client is not None or self._init_error is not None:
            return self._client
        if not self.configured:
            self._init_error = "GEMINI_API_KEY not set"
            return None
        try:
            from google import genai

            self._client = genai.Client(api_key=settings.gemini_api_key)
        except Exception as exc:  # pragma: no cover - depends on env
            self._init_error = f"Gemini init failed: {exc}"
            logger.warning(self._init_error)
        return self._client

    def _generate(self, contents: list) -> Optional[str]:
        client = self._get_client()
        if client is None:
            return None
        try:
            from google.genai import types

            resp = client.models.generate_content(
                model=settings.gemini_model,
                contents=contents,
                config=types.GenerateContentConfig(temperature=0.0),
            )
            return (resp.text or "").strip()
        except Exception as exc:  # pragma: no cover - network dependent
            logger.warning("Gemini generate_content failed: %s", exc)
            return None

    @staticmethod
    def _parse_json(text: str) -> Optional[dict[str, Any]]:
        if not text:
            return None
        t = text.strip()
        if t.startswith("```"):
            # strip ```json ... ``` fences
            t = t.split("```")[1] if "```" in t[3:] else t[3:]
            if t.lower().startswith("json"):
                t = t[4:]
            t = t.strip().strip("`").strip()
        try:
            return json.loads(t)
        except json.JSONDecodeError:
            start, end = t.find("{"), t.rfind("}")
            if 0 <= start < end:
                try:
                    return json.loads(t[start : end + 1])
                except json.JSONDecodeError:
                    return None
            return None

    def _image_part(self, image_bytes: Optional[bytes]):
        if not image_bytes:
            return None
        try:
            from PIL import Image

            return Image.open(io.BytesIO(image_bytes)).convert("RGB")
        except Exception as exc:
            logger.warning("Could not decode image for Gemini: %s", exc)
            return None

    def analyze(
        self,
        prompt: str,
        image_bytes: Optional[bytes] = None,
        identity_name: str = "Unknown",
        identity_known: bool = True,
    ) -> dict[str, Any]:
        """Holistic analysis. Returns a dict always containing `available`."""
        text = _ANALYSIS_PROMPT.format(
            identity=identity_name or "Unknown",
            is_unknown=str(not identity_known),
            prompt=prompt,
        )
        contents: list = []
        img = self._image_part(image_bytes)
        if img is not None:
            contents.append(img)
        contents.append(text)

        raw = self._generate(contents)
        if raw is None:
            return {"available": False, "reason": self._init_error or "gemini_call_failed"}

        data = self._parse_json(raw)
        if data is None:
            logger.warning("Gemini returned unparseable output")
            return {"available": False, "reason": "unparseable_ai_output"}

        data["available"] = True
        return data


gemini_client = GeminiClient()
