from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.auth.router import router as auth_router
from app.consent.router import router as consent_router
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging, get_logger
from app.db.database import init_db
from app.decision.router import router as decision_router
from app.identity.router import router as identity_router
from app.intent.router import router as intent_router
from app.logs.router import router as logs_router
from app.me.router import router as me_router
from app.permission.router import router as permission_router
from app.requests.router import router as requests_router
from app.risk.router import router as risk_router

logger = get_logger("main")


@asynccontextmanager
async def lifespan(_: FastAPI):
    configure_logging()
    problems = settings.insecure_settings()
    if problems:
        raise RuntimeError("Refusing to start in production: " + "; ".join(problems))
    init_db()
    logger.info("ARMOR backend started (db=%s)", settings.database_url.split("@")[-1])
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="ARMOR AI Safety Gateway — Identity → Consent → Trust",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)

for r in (
    auth_router,
    identity_router,
    permission_router,
    intent_router,
    risk_router,
    consent_router,
    decision_router,
    requests_router,
    logs_router,
    me_router,
):
    app.include_router(r)


@app.get("/", tags=["Meta"])
def root():
    return {"service": settings.app_name, "version": settings.app_version, "status": "running"}


@app.get("/health", tags=["Meta"])
def health():
    from app.ai.face import face_ai

    # Cheap status only: never triggers a model load here.
    return {
        "status": "ok",
        "ai": {
            "face_model_loaded": face_ai.loaded,
            "face_model_error": face_ai.init_error,
        },
    }
