import logging
import uuid

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.auth.router import router as auth_router
from app.notes.router import router as notes_router
from app.vault.router import router as vault_router
from app.errors import APIError

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    app = FastAPI(title="super-secure-notes-api", version="0.1.0")

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

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(auth_router, prefix="/v1")
    app.include_router(vault_router, prefix="/v1")
    app.include_router(notes_router, prefix="/v1")

    return app


app = create_app()
