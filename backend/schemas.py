import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class _Base(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")


class RegisterIn(_Base):
    first_name: str = Field(min_length=1, max_length=60)
    last_name: str = Field(min_length=1, max_length=60)
    email: EmailStr
    username: str = Field(pattern=r"^[A-Za-z0-9_.-]{3,30}$")
    contact_number: str = Field(pattern=r"^\+?[0-9 ]{9,18}$")
    # Only these two roles can self-register. Admins are created with
    # `python -m app.create_admin`.
    role: Literal["Student", "Tutor"]
    password: str = Field(min_length=10, max_length=72)
    # Must confirm the privacy policy, and that they are 18+ or have
    # a parent/guardian's permission.
    consent: bool

    @field_validator("email")
    @classmethod
    def lower_email(cls, v: str) -> str:
        return v.lower()

    @field_validator("password")
    @classmethod
    def strong_password(cls, v: str) -> str:
        if len(v.encode()) > 72:  # bcrypt limit
            raise ValueError("Password is too long")
        if not (re.search(r"[A-Za-z]", v) and re.search(r"\d", v)):
            raise ValueError("Password must contain letters and numbers")
        return v

    @field_validator("consent")
    @classmethod
    def must_consent(cls, v: bool) -> bool:
        if not v:
            raise ValueError("Consent is required")
        return v


class LoginIn(_Base):
    email: EmailStr
    password: str = Field(min_length=1, max_length=200)

    @field_validator("email")
    @classmethod
    def lower_email(cls, v: str) -> str:
        return v.lower()


class ContactIn(_Base):
    name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    message: str = Field(min_length=5, max_length=2000)
    website: str = ""  # honeypot: real visitors never fill this in
