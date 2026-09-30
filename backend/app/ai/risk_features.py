"""Risk AI features: what the content is, never who agreed to it.

CLAUDE.md bagian 8: the Risk AI sees content features only (intent, confidence,
target type, media type, realism, manipulation, sensitive context, synthetic
voice). Consent and permissions are NOT features; the policy engine handles them.

realism, manipulation and sensitive_context are extracted from the prompt with the
documented keyword rules below (Fase 5 task 6). They are coarse on purpose: three
levels (0.1 low, 0.5 unknown/medium, 0.9 high) that annotators and the policy can
reason about. The same `vectorize` is used by ml/risk training and by the backend,
so the model always sees identical inputs.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass

from app.schema.common import Intent

LOW, MID, HIGH = 0.1, 0.5, 0.9

# --- Keyword rules -------------------------------------------------------------------

# The output should look like a real photo, video or voice.
REALISM_HIGH = (
    "fotorealistik",
    "realistis",
    "terlihat nyata",
    "seperti asli",
    "seperti foto asli",
    "mirip asli",
    "mirip banget",
    "suara asli",
    "hd",
    "4k",
    "deepfake",
    "photorealistic",
    "realistic",
    "looks real",
    "real photo",
    "lifelike",
    "hyperreal",
    "that looks real",
)
# The output is clearly stylized, so nobody mistakes it for reality.
REALISM_LOW = (
    "kartun",
    "karikatur",
    "anime",
    "ilustrasi",
    "lukisan",
    "sketsa",
    "pixel art",
    "komik",
    "chibi",
    "wayang",
    "stiker",
    "cat minyak",
    "suara kartun",
    "cartoon",
    "caricature",
    "illustration",
    "painting",
    "sketch",
    "comic",
    "sticker",
    "toon",
    "storybook",
)
# The person or what they say is substantially changed.
MANIPULATION_HIGH = (
    "ganti wajah",
    "tukar wajah",
    "face swap",
    "lip-sync",
    "lipsync",
    "lip sync",
    "tiru suara",
    "tiru suaranya",
    "kloning",
    "clon*",
    "seolah",
    "mengatakan",
    "berkata",
    "mengucapkan",
    "mengaku",
    "deepfake",
    "ubah ucapan",
    "pretend*",
    "saying",
    "appearing to say",
    "impersonat*",
    "copy his voice",
    "copy her voice",
    "sync her lips",
    "sync his lips",
    "gerakkan bibir",
)
# Light edits that keep the meaning of the original.
MANIPULATION_LOW = (
    "cerahkan",
    "mencerahkan",
    "perbaiki pencahayaan",
    "perbaiki warna",
    "stabilkan",
    "potong",
    "crop",
    "rapikan",
    "hapus jerawat",
    "kurangi suara bising",
    "hilangkan noise",
    "brighten",
    "fix the lighting",
    "color correct",
    "stabilize",
    "trim",
    "remove background noise",
    "denoise",
    "edit ringan",
    "tidy up",
)
# Contexts where harm spreads fast or hits vulnerable people.
SENSITIVE = (
    "anak",
    "bayi",
    "balita",
    "sekolah",
    "siswa",
    "agama",
    "masjid",
    "gereja",
    "pura",
    "vihara",
    "pemilu",
    "pilkada",
    "pilpres",
    "kampanye",
    "partai",
    "calon",
    "bencana",
    "gempa",
    "banjir",
    "tsunami",
    "rumah sakit",
    "obat",
    "vaksin",
    "polisi",
    "pengadilan",
    "jaksa",
    "kpk",
    "rekening",
    "minta transfer",
    "transfer uang",
    "bank",
    "otp",
    "bansos",
    "blt",
    "child*",
    "kid",
    "kids",
    "baby",
    "babies",
    "school*",
    "religio*",
    "mosque",
    "church",
    "election*",
    "vote",
    "voting",
    "campaign*",
    "political party",
    "candidate*",
    "disaster*",
    "earthquake*",
    "flood*",
    "hospital*",
    "vaccine*",
    "medicine",
    "police",
    "court",
    "bank account",
    "wire money",
)


def _has(text: str, words: tuple[str, ...]) -> bool:
    """Whole-word match ("kid" does not match "kidding"); a trailing "*" marks a
    stem that may continue ("impersonat*" matches "impersonate")."""
    for w in words:
        stem = w.endswith("*")
        core = re.escape(w.rstrip("*"))
        pattern = rf"(?<![a-z0-9]){core}" + ("" if stem else r"(?![a-z0-9])")
        if re.search(pattern, text):
            return True
    return False


def realism(prompt: str) -> float:
    t = (prompt or "").lower()
    if _has(t, REALISM_HIGH):
        return HIGH
    if _has(t, REALISM_LOW):
        return LOW
    return MID


def manipulation(prompt: str) -> float:
    t = (prompt or "").lower()
    if _has(t, MANIPULATION_HIGH):
        return HIGH
    if _has(t, MANIPULATION_LOW):
        return LOW
    return MID


def sensitive_context(prompt: str) -> int:
    return int(_has((prompt or "").lower(), SENSITIVE))


# --- Feature vector ---------------------------------------------------------------------

TARGET_TYPES = ("SELF", "OTHER_REGISTERED", "OTHER_UNREGISTERED", "UNCLEAR", "NONE")
MEDIA_TYPES = ("IMAGE", "VIDEO", "AUDIO", "TEXT_ONLY")
INTENTS = tuple(i.value for i in Intent)


@dataclass
class RiskFeatures:
    intent: str
    confidence: float
    target_type: str  # worst target in the request, or NONE
    media: str
    realism: float
    manipulation: float
    sensitive_context: int
    synthetic_voice: int  # from Voice AI anti-spoof (Fase 10b); 0 when unknown

    def as_dict(self) -> dict:
        return asdict(self)


def from_prompt(
    prompt: str,
    intent: str,
    confidence: float,
    target_type: str,
    media: str,
    synthetic_voice: int = 0,
) -> RiskFeatures:
    return RiskFeatures(
        intent=intent,
        confidence=float(confidence),
        target_type=target_type if target_type in TARGET_TYPES else "UNCLEAR",
        media=media if media in MEDIA_TYPES else "IMAGE",
        realism=realism(prompt),
        manipulation=manipulation(prompt),
        sensitive_context=sensitive_context(prompt),
        synthetic_voice=int(synthetic_voice),
    )


def feature_names() -> list[str]:
    return (
        [f"intent={i}" for i in INTENTS]
        + ["confidence"]
        + [f"target={t}" for t in TARGET_TYPES]
        + [f"media={m}" for m in MEDIA_TYPES]
        + ["realism", "manipulation", "sensitive_context", "synthetic_voice"]
    )


# Human-readable group per column, used for "top 3 features" in ARMOR Explain.
def feature_group(name: str) -> str:
    return name.split("=", 1)[0]


def vectorize(f: RiskFeatures) -> list[float]:
    return (
        [1.0 if f.intent == i else 0.0 for i in INTENTS]
        + [f.confidence]
        + [1.0 if f.target_type == t else 0.0 for t in TARGET_TYPES]
        + [1.0 if f.media == m else 0.0 for m in MEDIA_TYPES]
        + [f.realism, f.manipulation, float(f.sensitive_context), float(f.synthetic_voice)]
    )


# Neutral values used to measure how much each feature group moves the score.
NEUTRAL = {
    "confidence": 1.0,
    "realism": MID,
    "manipulation": MID,
    "sensitive_context": 0,
    "synthetic_voice": 0,
    "target_type": "NONE",
    "media": "IMAGE",
    "intent": Intent.PERSONAL_EDITING.value,
}
