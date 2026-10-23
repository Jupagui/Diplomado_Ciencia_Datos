"""Fixtures compartidas. Nunca se usa backend/data/micronegocio.db."""
import os
import tempfile

# Antes de importar la app: apuntar a una BD temporal y a una clave Fernet fija.
_TMP = tempfile.mkdtemp(prefix="mn_tests_")
os.environ["DATABASE_URL"] = f"sqlite:///{_TMP.replace(os.sep, '/')}/import_guard.db"
os.environ["FERNET_KEY"] = "KmDnBMyXjJ1v3Hq0m8cVQ0e1nX4oJ6k1y2zq5v0tq3k="
os.environ["SEED_ON_EMPTY"] = "false"

import pytest
from cryptography.fernet import Fernet
from sqlalchemy.orm import sessionmaker

from app.core.db import Base, crear_motor


@pytest.fixture(scope="session")
def fernet_key() -> str:
    return Fernet.generate_key().decode()


@pytest.fixture
def cipher(fernet_key):
    from app.adapters.outbound.crypto.fernet_cipher import FernetCipher
    return FernetCipher(fernet_key)


@pytest.fixture
def db_engine(tmp_path):
    from app.adapters.outbound.persistence import models  # noqa: F401
    motor = crear_motor(f"sqlite:///{(tmp_path / 'test.db').as_posix()}")
    Base.metadata.create_all(motor)
    yield motor
    motor.dispose()


@pytest.fixture
def session_factory(db_engine):
    return sessionmaker(bind=db_engine, expire_on_commit=False)


@pytest.fixture
def db_session(session_factory):
    with session_factory() as s:
        yield s
