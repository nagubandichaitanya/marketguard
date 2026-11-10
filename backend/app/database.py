from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from backend.app.config import settings


database_url = URL.create(
    drivername="postgresql+psycopg",
    username=settings.postgres_user,
    password=settings.postgres_password,
    host=settings.postgres_host,
    port=settings.postgres_port,
    database=settings.postgres_db,
)

engine = create_engine(database_url, pool_pre_ping=True)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def test_connection():
    with engine.connect() as connection:
        result = connection.execute(text("SELECT version();"))
        return result.scalar()