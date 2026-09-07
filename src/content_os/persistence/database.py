"""SQLAlchemy engine and schema lifecycle."""

from functools import lru_cache

from sqlalchemy import Engine, create_engine

from content_os.config import get_settings
from content_os.persistence.tables import Base


def build_engine(database_url: str) -> Engine:
    options = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    return create_engine(database_url, connect_args=options)


@lru_cache
def get_engine() -> Engine:
    return build_engine(get_settings().database_url)


def initialize_database(engine: Engine) -> None:
    """Create tables for local development; production uses Alembic migrations."""

    Base.metadata.create_all(engine)
