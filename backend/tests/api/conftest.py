import pytest
from fastapi.testclient import TestClient

from app.adapters.inbound.api import deps
from app.adapters.outbound.persistence.repositories import UserRepoSQL
from app.core.db import get_session
from app.core.security import hashear_password
from app.domain.entities import Usuario
from app.main import app


@pytest.fixture
def client(db_engine, session_factory, cipher):
    with session_factory() as s:
        UserRepoSQL(s).crear(Usuario("admin", hashear_password("admin123"), True))
        s.commit()

    def _sesion():
        with session_factory() as s:
            yield s

    app.dependency_overrides[get_session] = _sesion
    app.dependency_overrides[deps.get_cipher] = lambda: cipher
    # Sin "with": no ejecuta el lifespan (que usaría la BD real).
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def token(client):
    r = client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin123"})
    return r.json()["access_token"]


@pytest.fixture
def auth(token):
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def mk_producto(client, auth):
    def _mk(sku="P-1", name="Cafe", price=1000, cost=400, stock=10, category="Bebidas"):
        r = client.post("/api/v1/products", headers=auth, json={
            "sku": sku, "name": name, "unit_price": price, "unit_cost": cost, "stock": stock,
            "category": category})
        assert r.status_code == 201, r.text
        return r.json()
    return _mk
