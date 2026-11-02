# LearnHub

Tutoring website: public pages, student / tutor / admin accounts, contact form.
FastAPI + PostgreSQL backend, plain HTML/CSS/JS frontend (no build step, no CDNs).

## Run it locally

```bash
cp .env.example .env          # then fill in SECRET_KEY and POSTGRES_PASSWORD
docker compose up --build     # site at http://localhost:8000
docker compose exec web python -m app.create_admin   # create your admin login
```

Without Docker: create a venv, `pip install -r requirements-dev.txt`, set `DATABASE_URL` in `.env`,
then `uvicorn app.main:app --reload`.

## Run the tests

```bash
pip install -r requirements-dev.txt
pytest
```

## Project layout

```
app/                 backend
  main.py            app setup, security headers, CSRF check
  routes.py          pages + API endpoints
  security.py        password hashing, login sessions, rate limits
  schemas.py         input validation
  models.py          database tables
  create_admin.py    command to create an admin
frontend/pages/      HTML (served by routes.py, dashboards need login)
frontend/static/     CSS, JS, images (the only public folder)
tests/               automated tests
```

## Security summary

- Passwords hashed with bcrypt; never returned by any endpoint.
- Login uses an HttpOnly, SameSite cookie (Secure in production). Roles are checked on the server, every request.
- Only Student and Tutor can self-register. Admins are created from the command line.
- Login, registration and contact form are rate limited. Wrong-login messages are identical for unknown email and wrong password.
- Strict Content-Security-Policy, so inline scripts and outside scripts are blocked.
- Cross-site POST requests are rejected. API docs are switched off.
- No secrets in the repo: everything comes from environment variables.

## Deploying to Azure (devant.co.za)

1. In the Azure Web App, set Application settings: `APP_ENV=production`, `SECRET_KEY=<long random string>`,
   `DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST:5432/DBNAME` (use Azure Database for PostgreSQL),
   and `SCM_DO_BUILD_DURING_DEPLOYMENT=true`.
2. Set the Startup Command to:
   `python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips=*`
3. Make sure the Python version in Azure matches `PYTHON_VERSION` in `.github/workflows/deploy.yml`.
4. Add the custom domain `devant.co.za` in Azure (Custom domains), create the DNS records Azure shows you at your
   registrar, then add the free managed certificate. Turn on "HTTPS Only".
5. Run `python -m app.create_admin` once from the Azure SSH console.

Pushing to `main` runs the tests and deploys.

## Before you launch

- Fill in the `[PLACEHOLDERS]` in `frontend/pages/privacy.html` and `terms.html` and get them reviewed by an attorney.
- Register your Information Officer with the Information Regulator.
- Get permission from everyone shown in the review screenshots (`frontend/static/images/1-4.jpeg`).
- Rotate any password that was ever committed to Git (the old database password).
