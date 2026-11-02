from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from config import DATABASE_URL
from models import metadata

if DATABASE_URL.startswith("sqlite"):  # used by the automated tests only
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
else:
   
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)


def init_db() -> None:
    """Create any missing tables."""
    metadata.create_all(engine)
