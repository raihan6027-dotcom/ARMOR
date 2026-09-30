"""Import all models so they register on Base.metadata."""

from app.models.consent import Consent
from app.models.identity import Identity
from app.models.permission import Permission
from app.models.request import Request
from app.models.user import User

__all__ = ["User", "Identity", "Permission", "Request", "Consent"]
