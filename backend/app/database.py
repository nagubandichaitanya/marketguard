"""Database engine/session setup will be completed in the PostgreSQL checkpoint."""

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from backend.app.config import settings


def build_database_url() -> str:
    return (
        f"postgresql+psycopg://{settings.postgres_user}:"
        f"{settings.postgres_password}@{settings.postgres_host}:"
        f"{settings.postgres_port}/{settings.postgres_db}"
    )


class Base(DeclarativeBase):
    pass


engine = create_engine(build_database_url(), pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db():
    """FastAPI dependency; callers should close the yielded session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
