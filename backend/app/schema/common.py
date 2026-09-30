"""Canonical enums for the ARMOR domain plus normalizers that map noisy AI /
free-text output onto those enums. AI output is NEVER trusted verbatim: anything
unrecognized collapses to a safe, explicit "unknown/uncertain" value so the
deterministic policy engine can fall back to REVIEW instead of mis-deciding."""

from enum import Enum


class IdentityTarget(str, Enum):
    SELF = "SELF"
    OTHER = "OTHER"
    UNKNOWN = "UNKNOWN"


class Intent(str, Enum):
    PERSONAL_CREATION = "PERSONAL_CREATION"
    PERSONAL_EDITING = "PERSONAL_EDITING"
    COMMERCIAL_USE = "COMMERCIAL_USE"
    IMPERSONATION = "IMPERSONATION"
    DEFAMATION = "DEFAMATION"
    POLITICAL_USE = "POLITICAL_USE"
    DECEPTIVE = "DECEPTIVE"
    UNCERTAIN = "UNCERTAIN"


class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class PermissionDecision(str, Enum):
    ALLOW = "ALLOW"
    REVIEW = "REVIEW"
    DENY = "DENY"


class ConsentStatus(str, Enum):
    GRANTED = "GRANTED"
    DENIED = "DENIED"
    PENDING = "PENDING"
    UNKNOWN = "UNKNOWN"


class Decision(str, Enum):
    ALLOW = "ALLOW"
    REVIEW = "REVIEW"
    DENY = "DENY"


# --- Normalizers -----------------------------------------------------------

# Keyword -> canonical Intent. Order matters: earlier, more specific concepts win.
_INTENT_KEYWORDS: list[tuple[Intent, tuple[str, ...]]] = [
    (
        Intent.IMPERSONATION,
        (
            "imperson",
            "pretend",
            "say something",
            "mengatakan",
            "seolah",
            "fake statement",
            "put words",
        ),
    ),
    (
        Intent.DEFAMATION,
        (
            "defam",
            "slander",
            "pencemaran",
            "humiliat",
            "mempermalukan",
            "arrest",
            "tahanan",
            "borgol",
            "criminal",
            "drug",
            "narkob",
        ),
    ),
    (
        Intent.DECEPTIVE,
        (
            "deceiv",
            "deceptive",
            "mislead",
            "menipu",
            "hoax",
            "disinformasi",
            "scam",
        ),
    ),
    (
        Intent.POLITICAL_USE,
        (
            "political",
            "politik",
            "campaign",
            "kampanye",
            "election",
            "pemilu",
            "flag",
            "bendera",
            "speech",
            "pidato",
            "podium",
        ),
    ),
    (
        Intent.COMMERCIAL_USE,
        (
            "commercial",
            "komersial",
            "promot",
            "mempromosikan",
            "advertis",
            "iklan",
            "endorse",
            "product",
            "produk",
            "brand",
            "sponsor",
        ),
    ),
    (
        Intent.PERSONAL_EDITING,
        (
            "edit",
            "retouch",
            "enhance",
            "perbaiki",
            "filter",
        ),
    ),
    (
        Intent.PERSONAL_CREATION,
        (
            "avatar",
            "cartoon",
            "kartun",
            "personal",
            "pribadi",
            "profile pic",
            "selfie",
            "portrait",
        ),
    ),
]


def normalize_intent(value: str | None) -> Intent:
    if not value:
        return Intent.UNCERTAIN
    v = str(value).strip()
    # Exact enum name / value match first.
    for member in Intent:
        if v.upper() == member.value or v.upper() == member.name:
            return member
    low = v.lower()
    for intent, keywords in _INTENT_KEYWORDS:
        if any(k in low for k in keywords):
            return intent
    return Intent.UNCERTAIN


def normalize_risk(value: str | None) -> RiskLevel | None:
    if value is None:
        return None
    v = str(value).strip().upper()
    mapping = {
        "LOW": RiskLevel.LOW,
        "MEDIUM": RiskLevel.MEDIUM,
        "MED": RiskLevel.MEDIUM,
        "HIGH": RiskLevel.HIGH,
        "CRITICAL": RiskLevel.CRITICAL,
        "SEVERE": RiskLevel.CRITICAL,
    }
    return mapping.get(v)  # None => invalid AI output => caller uses safe fallback


def normalize_consent(value: str | None) -> ConsentStatus:
    if value is None:
        return ConsentStatus.UNKNOWN
    v = str(value).strip().upper()
    mapping = {
        "GRANTED": ConsentStatus.GRANTED,
        "APPROVED": ConsentStatus.GRANTED,
        "APPROVE": ConsentStatus.GRANTED,
        "ALLOW": ConsentStatus.GRANTED,
        "DENIED": ConsentStatus.DENIED,
        "DENY": ConsentStatus.DENIED,
        "REJECTED": ConsentStatus.DENIED,
        "PENDING": ConsentStatus.PENDING,
        "REQUESTED": ConsentStatus.PENDING,
        "NOT_GRANTED": ConsentStatus.UNKNOWN,
        "UNKNOWN": ConsentStatus.UNKNOWN,
    }
    return mapping.get(v, ConsentStatus.UNKNOWN)


def normalize_permission(value: str | None) -> PermissionDecision | None:
    if value is None:
        return None
    v = str(value).strip().upper()
    try:
        return PermissionDecision(v)
    except ValueError:
        return None


def risk_score_to_level(score: int | float | None) -> RiskLevel | None:
    if score is None:
        return None
    try:
        s = float(score)
    except (TypeError, ValueError):
        return None
    if s < 30:
        return RiskLevel.LOW
    if s < 60:
        return RiskLevel.MEDIUM
    if s < 85:
        return RiskLevel.HIGH
    return RiskLevel.CRITICAL
