import logging

from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.database import get_db
from app.models.user import User
from app.routers.auth_ui import require_admin, verify_csrf
from app.routers.ui import templates
from app.services.user_service import create_user, update_user, hash_password
from app.schemas.user import UserCreate

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin)])

VALID_ROLES = ("user", "spravce", "admin")


def flash(request: Request, message: str, category: str = "info") -> None:
    request.session.setdefault("_flash_messages", []).append((category, message))


@router.get("/uzivatele", response_class=HTMLResponse)
def users_list(request: Request, db: Session = Depends(get_db)):
    users = db.scalars(select(User).order_by(User.username)).all()
    return templates.TemplateResponse("admin/users.html", {
        "request": request,
        "users": users,
        "valid_roles": VALID_ROLES,
    })


@router.post("/uzivatele")
async def user_create(
    request: Request,
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    role: str = Form("user"),
    db: Session = Depends(get_db),
    _csrf=Depends(verify_csrf),
):
    if role not in VALID_ROLES:
        role = "user"
    try:
        create_user(db, UserCreate(username=username, email=email, password=password, role=role))
        logger.info(f"AUDIT: admin '{request.session.get('username')}' vytvořil uživatele '{username}' (role={role})")
        flash(request, f"Uživatel {username} byl vytvořen.", "success")
    except ValueError as e:
        flash(request, str(e), "danger")
    except Exception as e:
        logger.error(f"Chyba při vytváření uživatele '{username}': {e}")
        flash(request, "Nastala chyba při vytváření uživatele.", "danger")
    return RedirectResponse("/admin/uzivatele", status_code=303)


@router.post("/uzivatele/{user_id}/role")
async def user_set_role(
    user_id: int,
    request: Request,
    role: str = Form(...),
    db: Session = Depends(get_db),
    _csrf=Depends(verify_csrf),
):
    if role not in VALID_ROLES:
        flash(request, "Neplatná role.", "danger")
        return RedirectResponse("/admin/uzivatele", status_code=303)
    user = db.get(User, user_id)
    if user:
        old_role = user.role
        user.role = role
        db.commit()
        if request.session.get("user_id") == user_id:
            request.session["role"] = role
        logger.info(f"AUDIT: admin '{request.session.get('username')}' změnil roli '{user.username}': {old_role} → {role}")
        flash(request, f"Role uživatele {user.username} změněna na {role}.", "success")
    return RedirectResponse("/admin/uzivatele", status_code=303)


@router.post("/uzivatele/{user_id}/toggle")
async def user_toggle_active(
    user_id: int,
    request: Request,
    db: Session = Depends(get_db),
    _csrf=Depends(verify_csrf),
):
    # Prevent deactivating yourself
    if request.session.get("user_id") == user_id:
        flash(request, "Nemůžete deaktivovat vlastní účet.", "danger")
        return RedirectResponse("/admin/uzivatele", status_code=303)
    user = db.get(User, user_id)
    if user:
        user.is_active = not user.is_active
        db.commit()
        state = "aktivován" if user.is_active else "deaktivován"
        logger.info(f"AUDIT: admin '{request.session.get('username')}' {state} uživatele '{user.username}'")
        flash(request, f"Uživatel {user.username} byl {state}.", "success")
    return RedirectResponse("/admin/uzivatele", status_code=303)


@router.post("/uzivatele/{user_id}/password")
async def user_change_password(
    user_id: int,
    request: Request,
    password: str = Form(...),
    db: Session = Depends(get_db),
    _csrf=Depends(verify_csrf),
):
    user = db.get(User, user_id)
    if user and password:
        user.hashed_password = hash_password(password)
        db.commit()
        flash(request, f"Heslo uživatele {user.username} bylo změněno.", "success")
    return RedirectResponse("/admin/uzivatele", status_code=303)
