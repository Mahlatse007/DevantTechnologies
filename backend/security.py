import time
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
import jwt
from fastapi import Depends, HTTPException, Request
from sqlalchemy import select

from config import SECRET_KEY, SESSION_COOKIE, SESSION_HOURS
from database import engine
from models import users


# ---------- passwords ----------

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=12)).decode()


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), password_hash.encode())
    except ValueError:
        return False


# Checked when the email is unknown, so response time doesn't reveal
# whether an account exists.
DUMMY_HASH = hash_password("not-a-real-password")


# ---------- session token ----------

def create_token(user_id: int) -> str:
    exp = datetime.now(timezone.utc) + timedelta(hours=SESSION_HOURS)
    return jwt.encode({"sub": str(user_id), "exp": exp}, SECRET_KEY, algorithm="HS256")


def _user_from_request(request: Request) -> Optional[dict]:
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        return None
    try:
        data = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        user_id = int(data["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        return None
    # Role and active status always come from the database, never the token.
    with engine.connect() as conn:
        row = conn.execute(select(users).where(users.c.id == user_id)).mappings().first()
    if row is None or not row["is_active"]:
        return None
    return dict(row)


def optional_user(request: Request) -> Optional[dict]:
    return _user_from_request(request)


def current_user(user: Optional[dict] = Depends(optional_user)) -> dict:
    if user is None:
        raise HTTPException(status_code=401, detail="Please log in.")
    return user


def require_admin(user: dict = Depends(current_user)) -> dict:
    if user["role"] != "Admin":
        raise HTTPException(status_code=403, detail="Not allowed.")
    return user

def require_role(role: str):
    def dependency(user: dict = Depends(current_user)) -> dict:
        if user["role"] != role:
            raise HTTPException(status_code=403, detail="Not allowed.")
        return user
    return dependency

# ---------- rate limiting (in memory, per server process) ----------
class RateLimiter:
    def __init__(self, max_calls: int, window_seconds: int):
        self.max_calls = max_calls
        self.window = window_seconds
        self.hits: dict[str, deque] = defaultdict(deque)

    def check(self, key: str) -> None:
        now = time.monotonic()
        q = self.hits[key]
        while q and now - q[0] > self.window:
            q.popleft()
        if len(q) >= self.max_calls:
            raise HTTPException(status_code=429, detail="Too many attempts. Please try again later.")
        q.append(now)

    def reset(self) -> None:
        self.hits.clear()


def client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"
