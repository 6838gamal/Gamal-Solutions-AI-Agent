import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.core.config import settings


def _build_engine():
    db_url = settings.DB_URL
    # Replit's internal PostgreSQL does not require SSL; external DBs may.
    # Detect Replit-managed DB by checking for the PGHOST env var pattern.
    pghost = os.environ.get("PGHOST", "")
    if pghost and "render.com" not in pghost and "supabase" not in pghost:
        connect_args = {}
    else:
        connect_args = {"sslmode": "require"}

    return create_engine(
        db_url,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
        connect_args=connect_args,
    )


engine = _build_engine()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
