from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.ai.router import media_type_for
from app.auth.deps import get_current_user
from app.core.exceptions import ArmorError
from app.core.uploads import read_upload
from app.db.database import get_db
from app.models.user import User
from app.schema.request import (
    RequestCreate,
    RequestDecisionResponse,
    RequestDetail,
    RequestHistoryResponse,
)
from app.schema.shield import GenerateRequest, GenerateResponse
from app.services import decision_service, generation_service

router = APIRouter(prefix="/requests", tags=["Requests"])


@router.post("", response_model=RequestDecisionResponse)
def create_request(
    payload: RequestCreate,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    """Gateway ARMOR: periksa permintaan (gambar, video, audio, atau teks saja) sebelum
    konten dibuat. Hasilnya ALLOW, REVIEW (ditahan menunggu persetujuan atau peninjauan),
    atau DENY, dengan alasan dan saran prompt."""
    attached = [k for k in ("image", "video", "audio") if getattr(payload, k)]
    if len(attached) > 1:
        raise ArmorError("ONE_MEDIA_ONLY", "Attach at most one of image, video, or audio.", 422)
    image = read_upload(payload.image, "image", "image") if payload.image else None
    video = read_upload(payload.video, "video", "video") if payload.video else None
    audio = read_upload(payload.audio, "audio", "audio") if payload.audio else None
    result = decision_service.orchestrate(
        db,
        requester_user_id=current.user_id,
        prompt=payload.prompt,
        image_bytes=image,
        video_bytes=video,
        audio_bytes=audio,
        media_type=media_type_for(payload.media_type, image, video, audio),
        allow_training=payload.allow_training,
    )
    return RequestDecisionResponse(**result)


@router.get("", response_model=RequestHistoryResponse)
def list_requests(
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    """Riwayat permintaan milik sendiri."""
    result = decision_service.history(db, requester_user_id=current.user_id, limit=limit)
    return RequestHistoryResponse(**result)


@router.get("/{request_id}", response_model=RequestDetail)
def get_request(
    request_id: str,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    """Status terbaru satu permintaan milik sendiri (misalnya setelah persetujuan dijawab)."""
    return RequestDetail(**decision_service.get_own(db, request_id, current.user_id))


@router.post("/{request_id}/generate", response_model=GenerateResponse)
def generate(
    request_id: str,
    payload: GenerateRequest,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    """Setelah ALLOW: buat konten lewat generator, periksa ulang hasilnya dengan Output
    Guard, lalu pasang ARMOR Shield (label AI, metadata, hash). Kirim ulang gambar yang
    sama persis dengan yang diperiksa (media tidak disimpan). Jika hasil memuat wajah
    terdaftar yang tidak diizinkan, hasil ditahan (HELD) dan pemiliknya diberi tahu."""
    image = read_upload(payload.image, "image", "image") if payload.image else None
    return GenerateResponse(**generation_service.generate(db, request_id, current.user_id, image))
