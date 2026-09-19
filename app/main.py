import logging
import uuid

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.auth.router import router as auth_router
from app.notes.router import router as notes_router
from app.notes.uploads import router as uploads_router
from app.privacy import router as privacy_router
from app.shares.router import router as shares_router
from app.vault.router import router as vault_router
from app.errors import APIError

logger = logging.getLogger(__name__)

OPENAPI_TAGS = [
    {
        "name": "auth",
        "description": "Account registration, login, JWT access tokens, and refresh token rotation.",
    },
    {
        "name": "vault",
        "description": "Opaque vault header storage and identity public key lookup for sharing.",
    },
    {
        "name": "notes",
        "description": "Note index, body, and attachment CRUD for the authenticated owner.",
    },
    {
        "name": "uploads",
        "description": "Chunked upload sessions for attachments larger than 10 MB.",
    },
    {
        "name": "sharing",
        "description": "Read-only note sharing between users via wrapped FEK grants.",
    },
    {
        "name": "health",
        "description": "Service health checks.",
    },
]


def create_app() -> FastAPI:
    app = FastAPI(
        title="super-secure-notes-api",
        version="1.0.0",
        description=(
            "REST backend for the superSecureNotes encrypted notes app. "
            "Stores opaque vault headers, note bodies, and attachments only — "
            "no decryption on the server."
        ),
        openapi_tags=OPENAPI_TAGS,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def request_logging_middleware(request: Request, call_next):
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        response = await call_next(request)
        user_id = getattr(request.state, "user_id", None)
        logger.info(
            "request completed",
            extra={"request_id": request_id, "user_id": user_id, "path": request.url.path},
        )
        return response

    @app.exception_handler(APIError)
    async def api_error_handler(_: Request, exc: APIError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": exc.error, "message": exc.message},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        _: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=400,
            content={"error": "validation_error", "message": "Invalid request body."},
        )

    @app.get("/health", tags=["health"], summary="Health check")
    async def health() -> dict[str, str]:
        """Returns 200 when the API process is running."""
        return {"status": "ok"}

    app.include_router(privacy_router)
    app.include_router(auth_router, prefix="/v1")
    app.include_router(vault_router, prefix="/v1")
    app.include_router(uploads_router, prefix="/v1")
    app.include_router(shares_router, prefix="/v1")
    app.include_router(notes_router, prefix="/v1")

    return app


app = create_app()
