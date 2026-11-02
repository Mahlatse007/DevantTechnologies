
import getpass
import re
import sys

from sqlalchemy import insert
from sqlalchemy.exc import IntegrityError

from .database import engine, init_db
from .models import users
from .security import hash_password


def main() -> None:
    init_db()
    first = input("First name: ").strip()
    last = input("Last name: ").strip()
    email = input("Email: ").strip().lower()
    username = input("Username: ").strip()
    password = getpass.getpass("Password (min 10 characters, letters and numbers): ")

    if not (first and last and re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email)):
        sys.exit("Please enter a name and a valid email.")
    if not re.fullmatch(r"[A-Za-z0-9_.-]{3,30}", username):
        sys.exit("Username must be 3-30 letters, numbers, _ . or -")
    if len(password) < 10 or len(password.encode()) > 72 or not (
        re.search(r"[A-Za-z]", password) and re.search(r"\d", password)
    ):
        sys.exit("Password must be 10-72 characters with letters and numbers.")

    try:
        with engine.begin() as conn:
            conn.execute(insert(users).values(
                first_name=first, last_name=last, email=email, username=username,
                contact_number="n/a", role="Admin",
                password_hash=hash_password(password), is_active=True,
            ))
    except IntegrityError:
        sys.exit("That email or username already exists.")
    print(f"Admin '{username}' created.")


if __name__ == "__main__":
    main()
