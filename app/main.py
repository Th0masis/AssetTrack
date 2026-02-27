from fastapi import FastAPI, Request
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from contextlib import asynccontextmanager
from jinja2 import pass_context
import os

from app.database import engine, SessionLocal
from app.database import Base
import app.models  # noqa — register all models
from app.models.user import User
from app.config import settings
from app.services.user_service import hash_password
from app.routers import health, items, locations, moves, audits, qr, export, scan, disposals
from app.routers import ui, auth_ui, admin_ui
import logging

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(application: FastAPI):
    # Ensure DB exists and tables are created (for dev mode without alembic)
    os.makedirs("data", exist_ok=True)
    Base.metadata.create_all(bind=engine)

    # Create first admin user if no users exist yet
    db = SessionLocal()
    try:
        if not db.query(User).first():
            admin = User(
                username=settings.FIRST_ADMIN_USER,
                email=f"{settings.FIRST_ADMIN_USER}@assettrack.local",
                hashed_password=hash_password(settings.FIRST_ADMIN_PASS),
                role="admin",
                is_active=True,
            )
            db.add(admin)
            db.commit()
            logger.info("Vytvořen první admin uživatel: %s", settings.FIRST_ADMIN_USER)
    finally:
        db.close()

    yield


app = FastAPI(
    title="AssetTrack",
    description="Interní inventarizační systém",
    version="1.4.0",
    lifespan=lifespan,
)

app.add_middleware(
    SessionMiddleware,
    secret_key=settings.SECRET_KEY,
    https_only=settings.APP_ENV == "production",
    same_site="lax",
)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        if settings.APP_ENV == "production":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response


app.add_middleware(SecurityHeadersMiddleware)
app.mount("/static", StaticFiles(directory="app/static"), name="static")


# --- Jinja2 flash helpers ---
@pass_context
def _get_flashed_messages(ctx, with_categories=False):
    request = ctx.get("request")
    if request is None:
        return []
    messages = request.session.pop("_flash_messages", [])
    if with_categories:
        return messages
    return [msg for _cat, msg in messages]


ui.templates.env.globals["get_flashed_messages"] = _get_flashed_messages
ui.templates.env.globals["csrf_token"] = auth_ui.get_csrf_token

# API routers
app.include_router(health.router)
app.include_router(items.router)
app.include_router(locations.router)
app.include_router(moves.router)
app.include_router(audits.router)
app.include_router(qr.router)
app.include_router(export.router)
app.include_router(scan.router)
app.include_router(disposals.router)

# Auth + UI routers
app.include_router(auth_ui.router)
app.include_router(admin_ui.router)
app.include_router(ui.router)
