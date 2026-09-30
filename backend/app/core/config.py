from pydantic_settings import BaseSettings, SettingsConfigDict

_DEV_JWT_SECRETS = {
    "change-me-in-production",
    "change-me-to-a-long-random-string",
    "ganti-dengan-hasil-gen-secrets",
}


class Settings(BaseSettings):
    # --- App ---
    app_name: str = "ARMOR Main Backend API"
    app_version: str = "0.2.0"

    # --- Database ---
    # Driver-agnostic SQLAlchemy URL. MySQL is the target for deployment; SQLite
    # is used as a zero-setup fallback for local dev / tests.
    #   MySQL example:  mysql+pymysql://root:password@localhost:3306/armor
    #   SQLite example: sqlite:///./armor.db
    database_url: str = "sqlite:///./armor.db"

    # --- Auth / JWT ---
    jwt_secret: str = "change-me-in-production"  # noqa: S105 - dev default, set JWT_SECRET
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24

    # --- CORS ---
    # Comma-separated list of allowed origins, or "*" for all (prototype default).
    cors_origins: str = "*"

    # --- AI: Gemini (intent / risk / analysis) ---
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.5-flash-lite"
    gemini_timeout: int = 30
    # Kept for the "separate AI microservice" architecture option (unused when
    # Gemini is called in-process, but never hardcode a URL in business logic).
    ai_service_url: str = "http://localhost:8001"
    ai_service_timeout: int = 10

    # --- AI: Face identity model (ArcFace / InsightFace) ---
    # Directory that holds the pre-deployment model artifacts.
    model_dir: str = r"C:\Project ARMOR\Pre Deployment\Model Gambar"
    face_registry_file: str = "official_face_registry.pkl"
    # InsightFace model pack (downloaded on first use if not cached).
    insightface_model: str = "buffalo_l"
    # Cosine-similarity threshold for a positive face match (from the team notebook).
    face_match_threshold: float = 0.40
    # Half-width of the gray zone around the threshold (scores inside => UNCLEAR/REVIEW).
    face_gray_margin: float = 0.05

    # --- Environment ---
    app_env: str = "dev"  # dev | production

    # --- Biometric embedding encryption (Fernet key, base64 url-safe 32 bytes) ---
    armor_embedding_key: str = ""

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
        return problems

    @property
    def cors_origin_list(self) -> list[str]:
        if self.cors_origins.strip() == "*":
            return ["*"]
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
