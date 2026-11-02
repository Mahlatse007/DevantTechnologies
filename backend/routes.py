from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import FileResponse, RedirectResponse
from sqlalchemy import insert, select, update
from sqlalchemy.exc import IntegrityError

from config import IS_PROD, PAGES_DIR, SESSION_COOKIE, SESSION_HOURS
from database import engine
from models import contact_messages, users
from schemas import ContactIn, LoginIn, RegisterIn
from security import (
    DUMMY_HASH, RateLimiter, client_ip, create_token, current_user,
    hash_password, optional_user, require_admin, verify_password,
)

router = APIRouter()
api = APIRouter(prefix="/api")

login_by_ip = RateLimiter(max_calls=20, window_seconds=15 * 60)
login_by_email = RateLimiter(max_calls=8, window_seconds=15 * 60)
register_limit = RateLimiter(max_calls=10, window_seconds=60 * 60)
contact_limit = RateLimiter(max_calls=5, window_seconds=60 * 60)

DASHBOARD = {"Student": "/student", "Tutor": "/tutor", "Admin": "/admin"}


def _public(user: dict) -> dict:
    """Only fields that are safe to send to the browser. Never the password hash."""
    return {
        "id": user["id"],
        "first_name": user["first_name"],
        "last_name": user["last_name"],
        "email": user["email"],
        "username": user["username"],
        "role": user["role"],
    }


# ---------------- pages ----------------

def _page(name: str) -> FileResponse:
    return FileResponse(PAGES_DIR / name)


@router.get("/", include_in_schema=False)
def home():
    return _page("index.html")


@router.get("/login", include_in_schema=False)
def login_page(user: Optional[dict] = Depends(optional_user)):
    if user:
        return RedirectResponse(DASHBOARD[user["role"]], status_code=303)
    return _page("login.html")


@router.get("/register", include_in_schema=False)
def register_page():
    return _page("register.html")

@router.get("/learnhub", include_in_schema=False)
def learnhub_page():
    return _page("learnhub.html")

@router.get("/privacy", include_in_schema=False)
def privacy_page():
    return _page("privacy.html")


@router.get("/terms", include_in_schema=False)
def terms_page():
    return _page("terms.html")


def _protected(role: str, filename: str):
    def handler(user: Optional[dict] = Depends(optional_user)):
        if user is None or user["role"] != role:
            return RedirectResponse("/login", status_code=303)
        return _page(filename)
    return handler


for _role, _path in DASHBOARD.items():
    router.add_api_route(
        _path, _protected(_role, f"{_role.lower()}.html"),
        methods=["GET"], include_in_schema=False,
    )


@router.get("/health", include_in_schema=False)
def health():
    return {"status": "ok"}


# ---------------- API: accounts ----------------

@api.post("/register", status_code=201)
def register(data: RegisterIn, request: Request):
    register_limit.check(client_ip(request))
    try:
        with engine.begin() as conn:
            conn.execute(insert(users).values(
                first_name=data.first_name,
                last_name=data.last_name,
                email=data.email,
                username=data.username,
                contact_number=data.contact_number,
                role=data.role,
                password_hash=hash_password(data.password),
                is_active=True,
                consent_at=datetime.now(timezone.utc),
            ))
    except IntegrityError:
        raise HTTPException(409, "An account with that email or username already exists.")
    return {"message": "Account created. You can now log in."}


@api.post("/login")
def login(data: LoginIn, request: Request, response: Response):
    login_by_ip.check(client_ip(request))
    login_by_email.check(data.email)

    with engine.connect() as conn:
        row = conn.execute(select(users).where(users.c.email == data.email)).mappings().first()

    # Same work and same message whether the email exists or not.
    password_ok = verify_password(data.password, row["password_hash"] if row else DUMMY_HASH)
    if not (row and password_ok and row["is_active"]):
        raise HTTPException(401, "Incorrect email or password.")

    response.set_cookie(
        SESSION_COOKIE,
        create_token(row["id"]),
        max_age=SESSION_HOURS * 3600,
        httponly=True,   # JavaScript cannot read it
        secure=IS_PROD,  # HTTPS only in production
        samesite="lax",
        path="/",
    )
    return {"redirect": DASHBOARD[row["role"]]}


@api.post("/logout")
def logout(response: Response):
    response.delete_cookie(SESSION_COOKIE, path="/")
    return {"message": "Logged out."}


@api.get("/me")
def me(user: dict = Depends(current_user)):
    return _public(user)


# ---------------- API: contact form ----------------

@api.post("/contact", status_code=201)
def contact(data: ContactIn, request: Request):
    contact_limit.check(client_ip(request))
    if data.website:  # honeypot filled in: a bot. Pretend it worked.
        return {"message": "Thank you. We'll reply within 24 hours."}
    with engine.begin() as conn:
        conn.execute(insert(contact_messages).values(
            name=data.name, email=data.email, message=data.message,
        ))
    return {"message": "Thank you. We'll reply within 24 hours."}


# ---------------- API: admin ----------------

@api.get("/admin/users")
def admin_users(_: dict = Depends(require_admin)):
    with engine.connect() as conn:
        rows = conn.execute(select(users).order_by(users.c.id)).mappings().all()
    return [
        {**_public(r), "contact_number": r["contact_number"],
         "is_active": r["is_active"], "created_at": r["created_at"].isoformat()}
        for r in rows
    ]


@api.post("/admin/users/{user_id}/toggle-active")
def admin_toggle(user_id: int, admin: dict = Depends(require_admin)):
    if user_id == admin["id"]:
        raise HTTPException(400, "You can't deactivate your own account.")
    with engine.begin() as conn:
        row = conn.execute(select(users.c.is_active).where(users.c.id == user_id)).first()
        if row is None:
            raise HTTPException(404, "User not found.")
        conn.execute(update(users).where(users.c.id == user_id).values(is_active=not row[0]))
    return {"is_active": not row[0]}


@api.get("/admin/messages")
def admin_messages(_: dict = Depends(require_admin)):
    with engine.connect() as conn:
        rows = conn.execute(
            select(contact_messages).order_by(contact_messages.c.id.desc()).limit(200)
        ).mappings().all()
    return [{**r, "created_at": r["created_at"].isoformat()} for r in rows]


router.include_router(api)
