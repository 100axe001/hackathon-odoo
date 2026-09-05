"""Engine and session factory. The only module that builds either."""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config.settings import settings


class Base(DeclarativeBase):
    """Declarative base every model inherits from."""


engine = create_engine(settings.database_url, pool_pre_ping=True, future=True)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_session() -> Generator[Session, None, None]:
    """Yield a session and always close it.

    Commits are left to the caller: a route that fails partway through should
    not persist half its work.
    """
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
