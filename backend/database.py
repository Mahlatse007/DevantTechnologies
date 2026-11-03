from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy import create_engine, func, insert, select

from config import DATABASE_URL
from models import metadata, subjects

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


if DATABASE_URL.startswith("sqlite"):  # used by the automated tests only
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
else:
    # echo is off on purpose: SQL logs can contain personal data.
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)

DEFAULT_SUBJECTS = [
    "Mathematics", "Mathematical Literacy", "Physical Sciences", "Life Sciences",
    "Accounting", "Business Studies", "Economics", "English", "Afrikaans",
    "Geography", "History", "Information Technology",
]


def init_db() -> None:

    metadata.create_all(engine)
    with engine.begin() as conn:
        if conn.execute(select(func.count()).select_from(subjects)).scalar() == 0:
            conn.execute(insert(subjects), [{"name": n} for n in DEFAULT_SUBJECTS])