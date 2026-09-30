from typing import Optional

from pydantic import BaseModel, Field


class GenerateRequest(BaseModel):
    """The very same image ARMOR checked (base64); omit for a text-only request."""

    image: Optional[str] = None


class ShieldInfo(BaseModel):
    shield_id: str
    created_at: str
    permission_status: str  # POLICY_ALLOWED | OWNER_PERMITTED
    permission_text: str
    label: str


class GeneratorInfo(BaseModel):
    name: str
    simulated: bool  # True: the mock generator (a simulation, not generative AI)


class GenerateResponse(BaseModel):
    request_id: str
    status: str  # DELIVERED | HELD (Output Guard)
    image: Optional[str] = None  # base64 PNG with the ARMOR Shield, only when DELIVERED
    message: str
    shield: Optional[ShieldInfo] = None
    generator: GeneratorInfo
    timing_ms: dict[str, int] = {}


class VerifyRequest(BaseModel):
    image: str = Field(description="Gambar yang ingin diperiksa (base64 PNG/JPEG/WebP).")


class VerifyResponse(BaseModel):
    verified: bool
    # METADATA (signed manifest) | HASH (same file or pixels) | PERCEPTUAL (similar) | NONE
    method: str
    exact: bool
    created_at: Optional[str] = None
    permission_status: Optional[str] = None
    permission_text: Optional[str] = None
    distance: Optional[int] = None  # perceptual hash distance (0-64), PERCEPTUAL only
    metadata_found: bool
    metadata_valid: bool
    simulated_generator: Optional[bool] = None
    message: str

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "verified": True,
                    "method": "METADATA",
                    "exact": True,
                    "created_at": "2026-09-30T08:15:02Z",
                    "permission_status": "POLICY_ALLOWED",
                    "permission_text": "Diizinkan oleh kebijakan ARMOR.",
                    "distance": None,
                    "metadata_found": True,
                    "metadata_valid": True,
                    "simulated_generator": True,
                    "message": "Gambar ini dibuat lewat ARMOR dan tidak diubah sejak itu.",
                }
            ]
        }
    }
