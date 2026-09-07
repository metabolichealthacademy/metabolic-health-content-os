"""SQLAlchemy engine and schema lifecycle."""

from functools import lru_cache

from sqlalchemy import Engine, create_engine, event

from content_os.config import get_settings
from content_os.persistence.tables import Base


def build_engine(database_url: str) -> Engine:
    options = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    engine = create_engine(database_url, connect_args=options)
    if database_url.startswith("sqlite"):

        @event.listens_for(engine, "connect")
        def enable_sqlite_foreign_keys(dbapi_connection: object, _: object) -> None:
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine


@lru_cache
def get_engine() -> Engine:
    return build_engine(get_settings().database_url)


def initialize_database(engine: Engine, environment: str = "development") -> None:
    """Create local tables; production schemas must be managed by Alembic."""

    if environment == "production":
        return
    Base.metadata.create_all(engine)
