import os

os.environ["DATABASE_URL"] = "sqlite://"
os.environ["APP_ENV"] = "development"
os.environ["SECRET_KEY"] = "test-secret-key-for-tests-only-0123456789"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import insert

from app.database import engine
from app.main import app
from app.models import metadata, users
from app.routes import contact_limit, login_by_email, login_by_ip, register_limit
from app.security import hash_password


@pytest.fixture()
def client():
    metadata.drop_all(engine)
    for limiter in (login_by_ip, login_by_email, register_limit, contact_limit):
        limiter.reset()
    with TestClient(app) as c:
        yield c


STUDENT = {
    "first_name": "Sipho", "last_name": "Dlamini", "email": "Sipho@Example.com",
    "username": "sipho_d", "contact_number": "0821234567", "role": "Student",
    "password": "Correct1horse", "consent": True,
}


def register(client, **overrides):
    return client.post("/api/register", json={**STUDENT, **overrides})


def login(client, email="sipho@example.com", password="Correct1horse"):
    return client.post("/api/login", json={"email": email, "password": password})


def make_admin():
    with engine.begin() as conn:
        conn.execute(insert(users).values(
            first_name="Ad", last_name="Min", email="admin@example.com", username="admin1",
            contact_number="n/a", role="Admin",
            password_hash=hash_password("AdminPass123"), is_active=True,
        ))
