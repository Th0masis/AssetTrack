import logging
import secrets
import time
from collections import defaultdict
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.services.user_service import verify_password, get_user_by_username

logger = logging.getLogger(__name__)

router = APIRouter(tags=["auth"])
templates = Jinja2Templates(directory="app/templates")

MANAGER_ROLES = {"spravce", "admin"}

# ── Rate limiting (in-memory, per IP) ──────────────────────────────────────
_login_attempts: dict[str, list[float]] = defaultdict(list)
_RATE_LIMIT_WINDOW = 60   # seconds
_RATE_LIMIT_MAX = 10      # max attempts per window


def _check_rate_limit(ip: str) -> bool:
    now = time.time()
    _login_attempts[ip] = [t for t in _login_attempts[ip] if now - t < _RATE_LIMIT_WINDOW]
    if len(_login_attempts[ip]) >= _RATE_LIMIT_MAX:
        return False
    _login_attempts[ip].append(now)
    return True


def _reset_rate_limit(ip: str) -> None:
    """Clear failed attempts after successful login."""
    _login_attempts.pop(ip, None)


# ── CSRF ───────────────────────────────────────────────────────────────────
def get_csrf_token(request: Request) -> str:
    """Return current session CSRF token, creating one if absent."""
    token = request.session.get("_csrf_token")
    if not token:
        token = secrets.token_hex(32)
        request.session["_csrf_token"] = token
    return token


async def verify_csrf(request: Request) -> None:
    """Dependency: verify CSRF token from POST form data."""
    form = await request.form()
    submitted = str(form.get("csrf_token", ""))
    expected = request.session.get("_csrf_token", "")
    if not expected or not secrets.compare_digest(expected, submitted):
        raise HTTPException(status_code=403, detail="Neplatný bezpečnostní token")


# ── Redirect helper ────────────────────────────────────────────────────────
def _safe_next(url: str) -> str:
    """Reject external/protocol-relative redirects, allow only same-origin paths."""
    parsed = urlparse(url)
    if parsed.scheme or parsed.netloc:
        return "/"
    return url if url.startswith("/") else "/"


def require_user(request: Request, db: Session = Depends(get_db)) -> User:
    """Dependency — redirects to /login if session is missing or invalid."""
    user_id = request.session.get("user_id")
    if not user_id:
        raise _redirect("/login")
    user = db.get(User, user_id)
    if not user or not user.is_active:
        request.session.clear()
        raise _redirect("/login")
    return user


def require_manager(user: User = Depends(require_user)) -> User:
    """Dependency — requires role spravce or admin."""
    if user.role not in MANAGER_ROLES:
        raise HTTPException(status_code=403, detail="Nedostatečná oprávnění")
    return user


def require_admin(user: User = Depends(require_user)) -> User:
    """Dependency — requires role admin."""
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Pouze pro administrátory")
    return user


def require_session_user(request: Request) -> None:
    """Light session-only check — any authenticated user."""
    if not request.session.get("user_id"):
        raise HTTPException(status_code=401, detail="Přihlášení vyžadováno")


def require_session_manager(request: Request) -> None:
    """Light session-only check for API mutation routes."""
    if not request.session.get("user_id"):
        raise HTTPException(status_code=401, detail="Přihlášení vyžadováno")
    role = request.session.get("role", "")
    if role not in MANAGER_ROLES:
        raise HTTPException(status_code=403, detail="Nedostatečná oprávnění")


def require_session_admin(request: Request) -> None:
    """Light session-only check — admin only."""
    if not request.session.get("user_id"):
        raise HTTPException(status_code=401, detail="Přihlášení vyžadováno")
    if request.session.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Pouze pro administrátory")


def _redirect(url: str):
    return HTTPException(status_code=302, headers={"Location": url})


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    if request.session.get("user_id"):
        return RedirectResponse("/", status_code=302)
    return templates.TemplateResponse("auth/login.html", {"request": request})


@router.post("/login", response_class=HTMLResponse)
def login_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    next: str = Form(default="/"),
    db: Session = Depends(get_db),
):
    ip = request.client.host if request.client else "unknown"
    if not _check_rate_limit(ip):
        return templates.TemplateResponse(
            "auth/login.html",
            {"request": request, "error": "Příliš mnoho pokusů. Zkuste to za chvíli.", "username": username},
            status_code=429,
        )
    user = get_user_by_username(db, username)
    if not user or not verify_password(password, user.hashed_password):
        logger.warning(f"AUDIT: neúspěšné přihlášení pro uživatele '{username}' z IP {ip}")
        return templates.TemplateResponse(
            "auth/login.html",
            {"request": request, "error": "Nesprávné jméno nebo heslo.", "username": username},
            status_code=401,
        )
    if not user.is_active:
        logger.warning(f"AUDIT: pokus o přihlášení deaktivovaného účtu '{username}' z IP {ip}")
        return templates.TemplateResponse(
            "auth/login.html",
            {"request": request, "error": "Účet je deaktivován.", "username": username},
            status_code=403,
        )
    _reset_rate_limit(ip)
    logger.info(f"AUDIT: přihlášení '{username}' (role={user.role}) z IP {ip}")
    request.session["user_id"] = user.id
    request.session["username"] = user.username
    request.session["role"] = user.role
    return RedirectResponse(_safe_next(next), status_code=302)


@router.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login", status_code=302)
