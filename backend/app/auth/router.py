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
    RegisterRequest,
    RegisterResponse,
    TokenResponse,
)

router = APIRouter(prefix="/auth", tags=["Auth"])


def _new_user_id() -> str:
    # UUIDs: row-count ids collided under concurrency and after deletions.
    return str(uuid.uuid4())


@router.post("/register", response_model=RegisterResponse, status_code=201)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise ArmorError("EMAIL_TAKEN", "An account with this email already exists.", 409)
    user = User(
        user_id=_new_user_id(),
        email=payload.email,
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return RegisterResponse(user_id=user.user_id, email=user.email)


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if user is None or not verify_password(payload.password, user.password_hash):
        raise AuthError("Invalid email or password.")
    token = create_access_token(subject=user.user_id, extra={"email": user.email})
    return TokenResponse(access_token=token, user_id=user.user_id)


@router.get("/me", response_model=MeResponse)
def me(current: User = Depends(get_current_user)):
    return MeResponse(user_id=current.user_id, email=current.email)
