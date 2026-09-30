"""Auth dependencies: extract and validate the bearer token, load the user."""

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.exceptions import AuthError
from app.core.security import decode_access_token
from app.db.database import get_db
from app.models.user import User

# auto_error=False so we can raise our own consistent error envelope.
_bearer = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None or not credentials.credentials:
        raise AuthError("Missing bearer token.")
    payload = decode_access_token(credentials.credentials)
    if not payload or "sub" not in payload:
        raise AuthError("Invalid or expired token.")
    user = db.query(User).filter(User.user_id == payload["sub"]).first()
    if user is None:
        raise AuthError("User no longer exists.")
    return user
