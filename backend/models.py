from sqlalchemy import (
    true,
    Boolean, Column, DateTime, Integer, MetaData, String, Table, Text, func,
)

from sqlalchemy import (
    Boolean, Column, DateTime, ForeignKey, Integer, MetaData, String, Table, Text,
    UniqueConstraint, func, true,
)

metadata = MetaData()

users = Table(
    "users",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("first_name", String(60), nullable=False),
    Column("last_name", String(60), nullable=False),
    Column("email", String(254), nullable=False, unique=True),
    Column("username", String(30), nullable=False, unique=True),
    Column("contact_number", String(20), nullable=False),
    Column("role", String(10), nullable=False),  # Student | Tutor | Admin
    Column("password_hash", String(100), nullable=False),
    Column("is_active", Boolean, nullable=False, server_default=true()),
    Column("consent_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
)

contact_messages = Table(
    "contact_messages",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("name", String(100), nullable=False),
    Column("email", String(254), nullable=False),
    Column("message", Text, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
)


subjects = Table(
    "subjects",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("name", String(60), nullable=False, unique=True),
)

# Which subjects each tutor teaches
tutor_subjects = Table(
    "tutor_subjects",
    metadata,
    Column("tutor_id", Integer, ForeignKey("users.id"), primary_key=True),
    Column("subject_id", Integer, ForeignKey("subjects.id"), primary_key=True),
)

# A one-hour time a tutor is available (stored in UTC)
slots = Table(
    "slots",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("tutor_id", Integer, ForeignKey("users.id"), nullable=False, index=True),
    Column("starts_at", DateTime(timezone=True), nullable=False),
    UniqueConstraint("tutor_id", "starts_at"),
)

# unique slot_id = a slot can only ever be booked once, even if two students click at the same moment
bookings = Table(
    "bookings",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("slot_id", Integer, ForeignKey("slots.id"), nullable=False, unique=True),
    Column("student_id", Integer, ForeignKey("users.id"), nullable=False, index=True),
    Column("subject_id", Integer, ForeignKey("subjects.id"), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
)
