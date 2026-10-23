"""Entorno compartido de Fase 2: BD temporal sembrada (120 dias, 80 clientes) + TestClient."""
from datetime import date

import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from app.adapters.inbound.api import deps
from app.adapters.outbound.crypto.fernet_cipher import FernetCipher
from app.adapters.outbound.persistence import models  # noqa: F401
from app.adapters.outbound.persistence.repositories import UserRepoSQL
from app.core.db import Base, crear_motor, get_session
from app.core.security import hashear_password
from app.domain.entities import Usuario
from app.main import app
from app.seed.generador_sintetico import sembrar


class Entorno:
    def __init__(self, ruta, dias=120, clientes=80):
        self.engine = crear_motor(f"sqlite:///{(ruta / 'f2.db').as_posix()}")
        Base.metadata.create_all(self.engine)
        self.sf = sessionmaker(bind=self.engine, expire_on_commit=False)
        self.cipher = FernetCipher(Fernet.generate_key())
        with self.sf() as s:
            UserRepoSQL(s).crear(Usuario("admin", hashear_password("admin123"), True))
            s.commit()
            sembrar(s, self.cipher, semilla=42, fin=date.today(), dias=dias, n_clientes=clientes)

        def _sesion():
            with self.sf() as s:
                yield s

        app.dependency_overrides[get_session] = _sesion
        app.dependency_overrides[deps.get_cipher] = lambda: self.cipher
        self.client = TestClient(app)
        tok = self.client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin123"})
        self.auth = {"Authorization": f"Bearer {tok.json()['access_token']}"}

    def cerrar(self):
        app.dependency_overrides.clear()
        self.engine.dispose()


def crear_entorno_fixture():
    @pytest.fixture(scope="module")
    def env(tmp_path_factory):
        e = Entorno(tmp_path_factory.mktemp("f2"))
        yield e
        e.cerrar()
    return env
