import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.core.exceptions import ArmorError, AuthError
from app.core.security import create_access_token, hash_password, verify_password
from app.db.database import get_db
from app.models.user import User
from app.schema.auth import (
    LoginRequest,
    MeResponse,
    MeUpdate,
    RegisterRequest,
    RegisterResponse,
    TokenResponse,
)

router = APIRouter(prefix="/auth", tags=["Auth"])


def _new_user_id() -> str:
    # UUIDs: row-count ids collided under concurrency and after deletions.
    return str(uuid.uuid4())


def _me(user: User) -> MeResponse:
    return MeResponse(
        user_id=user.user_id,
        email=user.email,
        role=user.role,
        display_name=user.display_name,
        email_notifications=user.email_notifications,
    )


@router.post("/register", response_model=RegisterResponse, status_code=201)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    email = payload.email.lower()
    if db.query(User).filter(User.email == email).first():
        raise ArmorError("EMAIL_TAKEN", "An account with this email already exists.", 409)
    # Every self-registered account is a USER; other roles only via the CLI.
    user = User(
        user_id=_new_user_id(),
        email=email,
        password_hash=hash_password(payload.password),
        role="USER",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return RegisterResponse(user_id=user.user_id, email=user.email)


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email.lower()).first()
    if user is None or not verify_password(payload.password, user.password_hash):
        raise AuthError("Invalid email or password.")
    token = create_access_token(subject=user.user_id, extra={"email": user.email})
    return TokenResponse(access_token=token, user_id=user.user_id)


@router.get("/me", response_model=MeResponse)
def me(current: User = Depends(get_current_user)):
    return _me(current)


@router.patch("/me", response_model=MeResponse)
def update_me(
    payload: MeUpdate,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    """Profil dan sakelar notifikasi email."""
    if payload.display_name is not None:
        current.display_name = payload.display_name.strip() or None
    if payload.email_notifications is not None:
        current.email_notifications = payload.email_notifications
    db.commit()
    db.refresh(current)
    return _me(current)
