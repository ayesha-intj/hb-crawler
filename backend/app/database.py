from collections.abc import Iterator
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from app.config import BACKEND_DIR, get_settings


class Base(DeclarativeBase):
    pass


def resolve_database_url(url: str) -> str:
    parsed = make_url(url)
    if parsed.get_backend_name() != "sqlite" or parsed.database in (
        None,
        "",
        ":memory:",
    ):
        return url

    path = Path(parsed.database)
    if not path.is_absolute():
        path = (BACKEND_DIR / path).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)

    return parsed.set(database=path.as_posix()).render_as_string(hide_password=False)


DATABASE_URL = resolve_database_url(get_settings().database_url)

# 1. Set up connection arguments based on the database type
connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

# 2. Pass it into the engine
engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def init_db() -> None:
    """Create all tables that do not exist yet."""
    from app import models  # noqa: F401 (import registers the models on Base)

    Base.metadata.create_all(bind=engine)


def get_session() -> Iterator[Session]:
    """FastAPI dependency: one session per request, always closed afterwards."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
