from sqlalchemy import (
    true,
    Boolean, Column, DateTime, Integer, MetaData, String, Table, Text, func,
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