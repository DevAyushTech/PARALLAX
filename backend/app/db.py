from collections.abc import Generator

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import get_settings


class Base(DeclarativeBase):
    pass


settings = get_settings()
connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    # Import models before create_all so every table is registered on Base.metadata.
    from . import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _upgrade_existing_sqlite_schema()


def _upgrade_existing_sqlite_schema() -> None:
    """Apply the one additive schema change needed by the MVP audit loop."""

    if engine.dialect.name != "sqlite":
        return
    columns = {column["name"] for column in inspect(engine).get_columns("evidence")}
    if "created_at" in columns:
        return
    with engine.begin() as connection:
        connection.execute(text("ALTER TABLE evidence ADD COLUMN created_at DATETIME"))
        connection.execute(text("UPDATE evidence SET created_at = timestamp WHERE created_at IS NULL"))
