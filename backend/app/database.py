import time

from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import settings

Base = declarative_base()

engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def wait_for_db(retries: int = 30, delay: float = 1.0) -> None:
    """Retries the initial DB connection so the backend can start before
    Postgres finishes accepting connections (compose healthcheck already
    covers most of this, but this is a cheap extra safety net)."""
    for attempt in range(1, retries + 1):
        try:
            with engine.connect():
                return
        except OperationalError:
            if attempt == retries:
                raise
            time.sleep(delay)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
