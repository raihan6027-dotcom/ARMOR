from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.ratelimit import limiter
from app.core.uploads import read_upload
from app.db.database import get_db
from app.schema.shield import VerifyRequest, VerifyResponse
from app.services import shield_service

router = APIRouter(prefix="/shield", tags=["Shield"])


@router.post("/verify", response_model=VerifyResponse)
def verify(payload: VerifyRequest, request: Request, db: Session = Depends(get_db)):
    """Verifikasi publik tanpa login: apakah gambar ini dibuat lewat ARMOR, kapan, dan
    status izinnya. Diperiksa berurutan: metadata bertanda tangan, hash, lalu
    perceptual hash. Jawaban tidak pernah memuat prompt, pembuat, atau siapa yang ada
    di gambar."""
    client = request.client.host if request.client else "unknown"
    limiter.check(f"verify:{client}", settings.public_verify_per_minute, 60)
    data = read_upload(payload.image, "image", "image")
    return VerifyResponse(**shield_service.verify(db, data))
