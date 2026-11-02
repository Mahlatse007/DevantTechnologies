from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from database import engine
from sqlalchemy import text
from schemas import RegisterIn
from routes import router
from pathlib import Path

from contextlib import asynccontextmanager
from urllib.parse import urlparse

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from config import IS_PROD, STATIC_DIR
from database import init_db
from routes import router


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


# Auto-generated API docs are switched off: no need to advertise the API.
app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)

CSP = (
    "default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; "
    "base-uri 'self'; form-action 'self'; frame-ancestors 'none'"
)


@app.exception_handler(RequestValidationError)
async def validation_error(_: Request, exc: RequestValidationError):
    # Friendly message plus the names of the fields to fix. Input values are never echoed back.
    fields = sorted({str(e["loc"][-1]) for e in exc.errors() if e.get("loc")})
    return JSONResponse(
        {"detail": "Please check your details and try again.", "fields": fields},
        status_code=422,
    )


@app.middleware("http")
async def security(request: Request, call_next):
    # CSRF protection: refuse state-changing requests that come from another site.
    if request.method in ("POST", "PUT", "PATCH", "DELETE"):
        origin = request.headers.get("origin")
        if origin and urlparse(origin).netloc != request.headers.get("host"):
            return JSONResponse({"detail": "Cross-site request blocked."}, status_code=403)

    response = await call_next(request)
    response.headers["Content-Security-Policy"] = CSP
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "same-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    if IS_PROD:
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    # Personal data and logged-in pages must never be cached.
    if not request.url.path.startswith("/static"):
        response.headers["Cache-Control"] = "no-store"
    return response


# Only /frontend/static is public. The HTML pages are served by routes.py,
# so the dashboards can't be opened without logging in.
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.include_router(router)
