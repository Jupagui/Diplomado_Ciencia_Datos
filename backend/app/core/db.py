"""Motor y sesión SQLAlchemy 2.0 síncronos (SQLite)."""
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.engine.url import make_url
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import get_settings


class Base(DeclarativeBase):
    pass


def crear_motor(url: str) -> Engine:
    u = make_url(url)
    es_sqlite = u.get_backend_name() == "sqlite"
    if es_sqlite and u.database and u.database != ":memory:":
        Path(u.database).parent.mkdir(parents=True, exist_ok=True)
    motor = create_engine(url, connect_args={"check_same_thread": False} if es_sqlite else {})
    if es_sqlite:
        @event.listens_for(motor, "connect")
        def _pragmas(dbapi_con, _):
            cur = dbapi_con.cursor()
            cur.execute("PRAGMA foreign_keys=ON")
            cur.close()
    return motor


engine = crear_motor(get_settings().database_url)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def get_session():
    with SessionLocal() as session:
        yield session
