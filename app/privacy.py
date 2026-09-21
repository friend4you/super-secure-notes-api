from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from app.config import settings

router = APIRouter(tags=["legal"])

_STATIC_DIR = Path(__file__).resolve().parent / "static"
_PRIVACY_HTML = (_STATIC_DIR / "privacy.html").read_text(encoding="utf-8")
_SUPPORT_HTML = (_STATIC_DIR / "support.html").read_text(encoding="utf-8")


def _render_static_html(template: str) -> str:
    return (
        template.replace("{{CONTACT_EMAIL}}", settings.privacy_contact_email)
        .replace("{{PRIVACY_URL}}", "/privacy")
    )


@router.get(
    "/privacy",
    response_class=HTMLResponse,
    summary="Privacy Policy",
    include_in_schema=False,
)
@router.get(
    "/privacy-policy",
    response_class=HTMLResponse,
    summary="Privacy Policy (alias)",
    include_in_schema=False,
)
async def privacy_policy() -> HTMLResponse:
    return HTMLResponse(content=_render_static_html(_PRIVACY_HTML))


@router.get(
    "/support",
    response_class=HTMLResponse,
    summary="Support",
    include_in_schema=False,
)
async def support_page() -> HTMLResponse:
    return HTMLResponse(content=_render_static_html(_SUPPORT_HTML))
