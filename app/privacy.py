from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from app.config import settings

router = APIRouter(tags=["legal"])

_STATIC_DIR = Path(__file__).resolve().parent / "static"
_PRIVACY_HTML = (_STATIC_DIR / "privacy.html").read_text(encoding="utf-8")


def _render_privacy_html() -> str:
    return _PRIVACY_HTML.replace("{{CONTACT_EMAIL}}", settings.privacy_contact_email)


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
    return HTMLResponse(content=_render_privacy_html())
