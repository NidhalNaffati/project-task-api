from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from app.core.config import settings


def get_engine() -> Engine:
    # Create engine at call time so environment variables/Settings overrides
    # (e.g., DATABASE_URL set in tests) are respected.
    return create_engine(settings.database_url)


engine = get_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
