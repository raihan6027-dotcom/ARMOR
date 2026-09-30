"""Consistent error envelope: every error response is `{"error": {"code","message"}}`."""

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.logging import get_logger

logger = get_logger("errors")


class ArmorError(Exception):
    """Domain error carrying a stable machine code and an HTTP status."""

    def __init__(self, code: str, message: str, status_code: int = status.HTTP_400_BAD_REQUEST):
        self.code = code
        self.message = message
        self.status_code = status_code
        super().__init__(message)


# Convenience factories for common cases.
class AuthError(ArmorError):
    def __init__(self, message: str = "Authentication failed"):
        super().__init__("UNAUTHORIZED", message, status.HTTP_401_UNAUTHORIZED)


class ForbiddenError(ArmorError):
    def __init__(self, message: str = "Not permitted"):
        super().__init__("FORBIDDEN", message, status.HTTP_403_FORBIDDEN)


class NotFoundError(ArmorError):
    def __init__(self, message: str = "Resource not found"):
        super().__init__("NOT_FOUND", message, status.HTTP_404_NOT_FOUND)


class AIServiceError(ArmorError):
    def __init__(self, message: str = "AI service error"):
        super().__init__("AI_SERVICE_ERROR", message, status.HTTP_502_BAD_GATEWAY)


class AIServiceTimeout(ArmorError):
    def __init__(self, message: str = "AI service timed out"):
        super().__init__("AI_SERVICE_TIMEOUT", message, status.HTTP_504_GATEWAY_TIMEOUT)


def _envelope(code: str, message: str, status_code: int, extra: dict | None = None) -> JSONResponse:
    body = {"error": {"code": code, "message": message}}
    if extra:
        body["error"].update(extra)
    return JSONResponse(status_code=status_code, content=body)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(ArmorError)
    async def _armor_error(_: Request, exc: ArmorError):
        logger.warning("ArmorError %s: %s", exc.code, exc.message)
        return _envelope(exc.code, exc.message, exc.status_code)

    @app.exception_handler(RequestValidationError)
    async def _validation_error(_: Request, exc: RequestValidationError):
        return _envelope(
            "VALIDATION_ERROR",
            "Request validation failed.",
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            {"details": exc.errors()},
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http_error(_: Request, exc: StarletteHTTPException):
        code = {
            400: "BAD_REQUEST",
            401: "UNAUTHORIZED",
            403: "FORBIDDEN",
            404: "NOT_FOUND",
            405: "METHOD_NOT_ALLOWED",
        }.get(exc.status_code, "HTTP_ERROR")
        return _envelope(code, str(exc.detail), exc.status_code)

    @app.exception_handler(Exception)
    async def _unhandled(_: Request, exc: Exception):
        logger.exception("Unhandled error: %s", exc)
        return _envelope(
            "INTERNAL_ERROR",
            "An internal error occurred.",
            status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
