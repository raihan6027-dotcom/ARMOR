"""Import all models so they register on Base.metadata."""

from app.models.audit import AuditLog
from app.models.biometric_consent import BiometricConsent
from app.models.case import Case, CaseEvent
from app.models.consent import Consent
from app.models.feedback import Feedback
from app.models.identity import Identity
from app.models.notification import Notification
from app.models.owner import Block, CircleMember
from app.models.permission import Permission
from app.models.request import Request
from app.models.request_target import RequestTarget
from app.models.user import User

__all__ = [
    "AuditLog",
    "BiometricConsent",
    "Block",
    "Case",
    "CaseEvent",
    "CircleMember",
    "Consent",
    "Feedback",
    "Identity",
    "Notification",
    "Permission",
    "Request",
    "RequestTarget",
    "User",
]
