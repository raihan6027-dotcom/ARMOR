"""Import all models so they register on Base.metadata."""

from app.models.biometric_consent import BiometricConsent
from app.models.case import Case
from app.models.consent import Consent
from app.models.identity import Identity
from app.models.permission import Permission
from app.models.request import Request
from app.models.request_target import RequestTarget
from app.models.user import User

__all__ = [
    "BiometricConsent",
    "Case",
    "Consent",
    "Identity",
    "Permission",
    "Request",
    "RequestTarget",
    "User",
]
