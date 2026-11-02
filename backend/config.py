"""Settings, read from environment variables (or a local .env file)."""
import os
import secrets
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parents[1]
PAGES_DIR = BASE_DIR / "frontend" / "pages"
STATIC_DIR = BASE_DIR / "frontend" / "static"

APP_ENV = os.getenv("APP_ENV", "development")
IS_PROD = APP_ENV == "production"

SECRET_KEY = os.getenv("SECRET_KEY", "")
if not SECRET_KEY:
    if IS_PROD:
        raise RuntimeError("SECRET_KEY must be set when APP_ENV=production")
    # Development only: sessions are lost whenever the server restarts.
    SECRET_KEY = secrets.token_urlsafe(48)

DATABASE_URL = os.getenv("DATABASE_URL", "")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set (see .env)")

SESSION_COOKIE = "session"
SESSION_HOURS = 8
