from sqlalchemy import select

from app.database import engine
from app.models import users
from .conftest import STUDENT, login, make_admin, register


def test_register_and_password_is_hashed(client):
    assert register(client).status_code == 201
    with engine.connect() as conn:
        row = conn.execute(select(users)).mappings().first()
    assert row["email"] == "sipho@example.com"
    assert row["password_hash"] != STUDENT["password"]
    assert row["password_hash"].startswith("$2")


def test_duplicate_email_rejected(client):
    register(client)
    assert register(client, username="other_name").status_code == 409


def test_cannot_register_as_admin(client):
    assert register(client, role="Admin").status_code == 422


def test_weak_password_and_missing_consent_rejected(client):
    assert register(client, password="short1").status_code == 422
    assert register(client, password="onlyletterslong").status_code == 422
    assert register(client, consent=False).status_code == 422


def test_login_wrong_password_is_generic_401(client):
    register(client)
    wrong_pw = login(client, password="Wrong-password1")
    wrong_email = login(client, email="nobody@example.com")
    assert wrong_pw.status_code == wrong_email.status_code == 401
    assert wrong_pw.json() == wrong_email.json()


def test_login_sets_httponly_cookie_and_me_hides_password(client):
    register(client)
    r = login(client)
    assert r.status_code == 200 and r.json()["redirect"] == "/student"
    assert "httponly" in r.headers["set-cookie"].lower()
    me = client.get("/api/me").json()
    assert me["email"] == "sipho@example.com"
    assert "password" not in str(me).lower()


def test_login_is_rate_limited(client):
    register(client)
    codes = [login(client, password="Wrong-password1").status_code for _ in range(9)]
    assert codes[-1] == 429


def test_dashboards_require_login_and_right_role(client):
    assert client.get("/student", follow_redirects=False).status_code == 303
    assert client.get("/admin", follow_redirects=False).status_code == 303
    register(client)
    login(client)
    assert client.get("/student").status_code == 200
    assert client.get("/admin", follow_redirects=False).status_code == 303
    assert client.get("/tutor", follow_redirects=False).status_code == 303


def test_admin_api_locked_down(client):
    register(client)
    assert client.get("/api/admin/users").status_code == 401
    login(client)
    assert client.get("/api/admin/users").status_code == 403
    client.post("/api/logout")

    make_admin()
    assert login(client, email="admin@example.com", password="AdminPass123").status_code == 200
    data = client.get("/api/admin/users").json()
    assert len(data) == 2
    assert all("password" not in str(u).lower() for u in data)


def test_old_users_endpoint_is_gone(client):
    assert client.get("/users").status_code == 404


def test_html_pages_not_directly_downloadable(client):
    for path in ("/static/student.html", "/static/pages/student.html", "/static/../app/main.py"):
        assert client.get(path).status_code == 404


def test_cross_site_post_blocked(client):
    r = client.post("/api/logout", headers={"Origin": "https://evil.example"})
    assert r.status_code == 403


def test_security_headers(client):
    r = client.get("/")
    assert "default-src 'self'" in r.headers["content-security-policy"]
    assert r.headers["x-frame-options"] == "DENY"


def test_contact_form_and_honeypot(client):
    body = {"name": "Thandi", "email": "t@example.com", "message": "Do you teach maths?"}
    assert client.post("/api/contact", json=body).status_code == 201
    assert client.post("/api/contact", json={**body, "website": "spam.com"}).status_code == 201
    make_admin()
    login(client, email="admin@example.com", password="AdminPass123")
    assert len(client.get("/api/admin/messages").json()) == 1  # bot message not stored
