from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_DEV_JWT_SECRETS = {
    "change-me-in-production",
    "change-me-to-a-long-random-string",
    "ganti-dengan-hasil-gen-secrets",
}

# backend/app/core/config.py -> repo root is three levels above backend/app/core.
REPO_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    # --- App ---
    app_name: str = "ARMOR Main Backend API"
    app_version: str = "0.3.0"
    app_env: str = "dev"  # dev | production

    # --- Database ---
    # Driver-agnostic SQLAlchemy URL. SQLite for local/offline demo and tests;
    # MySQL or PostgreSQL for deployment.
    database_url: str = "sqlite:///./armor.db"

    # --- Auth / JWT ---
    jwt_secret: str = "change-me-in-production"  # noqa: S105 - dev default, set JWT_SECRET
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24
    bcrypt_rounds: int = 12  # tests lower this; never below 12 in deployment

    # --- CORS ---
    # Comma-separated list of allowed origins, or "*" (dev only).
    cors_origins: str = "*"

    # --- Biometric embedding encryption (Fernet key, base64 url-safe 32 bytes) ---
    armor_embedding_key: str = ""

    # --- Local models (downloaded beforehand so the demo runs offline) ---
    model_dir: str = ""  # empty => <repo>/ml/models
    insightface_model: str = "buffalo_l"

    # --- Face AI thresholds ---
    # PLACEHOLDERS until ml/face_eval produces real values (docs/eval/face.md).
    # CLAUDE.md bagian 12: 0.40 was never derived from data.
    face_match_threshold: float = 0.40
    face_gray_margin: float = 0.05  # scores within +/- margin of the threshold => UNCLEAR
    # Enrollment: the 3 poses must look like the same person at least this much.
    face_same_person_threshold: float = 0.50
    # Quality gates (see app/ai/face.py).
    face_min_size_px: int = 80
    face_min_blur_var: float = 60.0
    face_max_yaw_deg: float = 45.0
    face_max_pitch_deg: float = 35.0
    # Enrollment liveness proxy: yaw spread across the 3 captures.
    face_min_pose_spread_deg: float = 8.0

    # --- Consent text versions (docs/consent-text/) ---
    consent_text_face: str = "face-v1"
    consent_text_voice: str = "voice-v1"

    # --- Upload limits ---
    max_image_mb: float = 8.0

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    def insecure_settings(self) -> list[str]:
        """Settings that are acceptable in dev but must never reach production."""
        problems = []
        if self.app_env.lower() == "production":
            if self.jwt_secret in _DEV_JWT_SECRETS or len(self.jwt_secret) < 32:
                problems.append("JWT_SECRET is a default or shorter than 32 characters")
            if self.cors_origins.strip() == "*":
                problems.append("CORS_ORIGINS must list the frontend origin, not '*'")
            if not self.armor_embedding_key:
                problems.append("ARMOR_EMBEDDING_KEY is not set")
            if self.bcrypt_rounds < 12:
                problems.append("BCRYPT_ROUNDS must be at least 12")
        return problems

    @property
    def model_root(self) -> str:
        return self.model_dir or str(REPO_ROOT / "ml" / "models")

    @property
    def cors_origin_list(self) -> list[str]:
        if self.cors_origins.strip() == "*":
            return ["*"]
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
