"""Canonical enums for the ARMOR domain (CLAUDE.md bagian 6) plus normalizers that
map noisy model / free-text output onto those enums. Model output is NEVER trusted
verbatim: anything unrecognized collapses to a safe, explicit value
(UNCERTAIN / NONE / None) so the policy engine can fail safe to REVIEW."""

from enum import Enum


class IdentityTarget(str, Enum):
    SELF = "SELF"
    OTHER_REGISTERED = "OTHER_REGISTERED"
    OTHER_UNREGISTERED = "OTHER_UNREGISTERED"
    UNCLEAR = "UNCLEAR"


class MediaType(str, Enum):
    IMAGE = "IMAGE"
    VIDEO = "VIDEO"
    AUDIO = "AUDIO"
    TEXT_ONLY = "TEXT_ONLY"


class TargetSource(str, Enum):
    FACE = "FACE"
    VOICE = "VOICE"
    TEXT = "TEXT"


class BiometricMedia(str, Enum):
    """The two biometric media an owner controls separately (Lock, permission)."""

    FACE = "FACE"
    VOICE = "VOICE"


class Intent(str, Enum):
    PERSONAL_CREATION = "PERSONAL_CREATION"
    PERSONAL_EDITING = "PERSONAL_EDITING"
    SATIRE_PARODY = "SATIRE_PARODY"
    COMMERCIAL_USE = "COMMERCIAL_USE"
    POLITICAL_USE = "POLITICAL_USE"
    IMPERSONATION = "IMPERSONATION"
    DEFAMATION = "DEFAMATION"
    SEXUAL_EXPLICIT = "SEXUAL_EXPLICIT"
    DECEPTIVE = "DECEPTIVE"
    UNCERTAIN = "UNCERTAIN"


# Intents that are always refused against another person (CLAUDE.md bagian 3, lapis 1).
HARMFUL_INTENTS: frozenset[Intent] = frozenset(
    {Intent.IMPERSONATION, Intent.DEFAMATION, Intent.SEXUAL_EXPLICIT, Intent.DECEPTIVE}
)

# Intents an owner can set a permission for (everything except UNCERTAIN).
PERMISSION_INTENTS: tuple[Intent, ...] = tuple(i for i in Intent if i is not Intent.UNCERTAIN)


class RiskLevel(str, Enum):
    LOW = "LOW"  # < 30
    MEDIUM = "MEDIUM"  # 30-59
    HIGH = "HIGH"  # 60-84
    CRITICAL = "CRITICAL"  # >= 85


class Decision(str, Enum):
    ALLOW = "ALLOW"
    REVIEW = "REVIEW"
    DENY = "DENY"


# Strictness order used to combine per-target decisions (DENY > REVIEW > ALLOW).
DECISION_RANK: dict[Decision, int] = {Decision.ALLOW: 0, Decision.REVIEW: 1, Decision.DENY: 2}


class ConsentStatus(str, Enum):
    GRANTED = "GRANTED"
    DENIED = "DENIED"
    PENDING = "PENDING"
    NONE = "NONE"


class LockLevel(str, Enum):
    NONE = "NONE"
    COMMERCIAL_POLITICAL = "COMMERCIAL_POLITICAL"
    ALL = "ALL"


class PermissionDecision(str, Enum):
    ALLOW = "ALLOW"
    REVIEW = "REVIEW"
    DENY = "DENY"


# --- Normalizers -----------------------------------------------------------

# Keyword -> canonical Intent, used only as the offline fallback when no trained
# Intent AI model is available. Order matters: harmful concepts are checked first
# so an ambiguous prompt is never classified into a more permissive class.
_INTENT_KEYWORDS: list[tuple[Intent, tuple[str, ...]]] = [
    (
        Intent.SEXUAL_EXPLICIT,
        (
            "telanjang",
            "bugil",
            "nude",
            "naked",
            "porn",
            "porno",
            "seksual",
            "sexual",
            "nsfw",
            "tanpa busana",
            "tanpa baju",
            "vulgar",
            "erotis",
            "erotic",
        ),
    ),
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
            "menyamar",
            "mengaku sebagai",
            "berpura-pura",
            "lip-sync",
            "lipsync",
        ),
    ),
    (
        Intent.DEFAMATION,
        (
            "defam",
            "slander",
            "pencemaran",
            "fitnah",
            "humiliat",
            "mempermalukan",
            "arrest",
            "tahanan",
            "borgol",
            "criminal",
            "kriminal",
            "drug",
            "narkob",
            "korupsi",
            "koruptor",
            "mabuk",
        ),
    ),
    (
        Intent.DECEPTIVE,
        (
            "deceiv",
            "deceptive",
            "mislead",
            "menipu",
            "penipuan",
            "hoax",
            "hoaks",
            "disinformasi",
            "scam",
            "biaya admin",
            "minta transfer",
            "transfer uang",
            "minta uang",
            "undian palsu",
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
            "pilkada",
            "flag",
            "bendera",
            "speech",
            "pidato",
            "podium",
            "partai",
            "calon",
            "coblos",
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
            "jualan",
            "diskon",
        ),
    ),
    (
        Intent.SATIRE_PARODY,
        (
            "satir",
            "satire",
            "parodi",
            "parody",
            "karikatur",
            "caricature",
            "meme",
            "lelucon",
        ),
    ),
    (
        Intent.PERSONAL_EDITING,
        ("edit", "retouch", "enhance", "perbaiki", "filter", "cerahkan", "mencerahkan"),
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
            "potret",
            "ilustrasi",
            "narasi",
        ),
    ),
]


def normalize_intent(value: str | None) -> Intent:
    if not value:
        return Intent.UNCERTAIN
    v = str(value).strip()
    for member in Intent:
        if v.upper() == member.value:
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
    return mapping.get(v)  # None => invalid model output => caller uses safe fallback


def normalize_consent(value: str | None) -> ConsentStatus:
    if value is None:
        return ConsentStatus.NONE
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
        "NONE": ConsentStatus.NONE,
        "UNKNOWN": ConsentStatus.NONE,
        "EXPIRED": ConsentStatus.NONE,
        "REVOKED": ConsentStatus.NONE,
    }
    return mapping.get(v, ConsentStatus.NONE)


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
