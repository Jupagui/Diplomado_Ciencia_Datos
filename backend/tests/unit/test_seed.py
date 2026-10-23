"""Generador sintético con muestra pequeña sobre BD temporal."""
from datetime import date

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import sessionmaker

from app.adapters.outbound.persistence import models as m
from app.core.db import Base, crear_motor
from app.seed.generador_sintetico import CATALOGO, base_vacia, sembrar


@pytest.fixture
def sembrada(db_session, cipher):
    assert base_vacia(db_session)
    conteos = sembrar(db_session, cipher, semilla=7, fin=date.today(), dias=30, n_clientes=25)
    return db_session, conteos


def test_conteos(sembrada):
    s, c = sembrada
    assert c["productos"] == len(CATALOGO) >= 40  # el catálogo real trae 41 (~40 según el plan)
    assert c["clientes"] == 25
    assert c["ventas"] > 0 and c["items"] >= c["ventas"]
    assert not base_vacia(s)
    assert s.scalar(select(func.count(m.SaleModel.id))) == c["ventas"]


def test_kardex_coherente(sembrada):
    s, _ = sembrada
    for p in s.scalars(select(m.ProductModel)):
        def suma(tipo):
            return s.scalar(select(func.coalesce(func.sum(m.InventoryMovementModel.quantity), 0)).where(
                m.InventoryMovementModel.product_id == p.id, m.InventoryMovementModel.movement_type == tipo))
        assert p.stock == suma("IN") - suma("OUT") >= 0, p.sku


def test_total_venta_igual_suma_items(sembrada):
    s, _ = sembrada
    for v in s.scalars(select(m.SaleModel)):
        suma = s.scalar(select(func.sum(m.SaleItemModel.subtotal)).where(m.SaleItemModel.sale_id == v.id))
        assert float(v.total_amount) == pytest.approx(float(suma))


def test_pii_cifrada_y_descifrable(sembrada, cipher):
    s, _ = sembrada
    c = s.scalars(select(m.CustomerModel)).first()
    assert "@" not in c.encrypted_email
    assert "@example.com" in cipher.descifrar(c.encrypted_email)
    assert cipher.descifrar(c.encrypted_phone).startswith("3")


def test_reproducible(tmp_path, cipher):
    kw = dict(semilla=11, fin=date(2026, 3, 31), dias=30, n_clientes=10)
    res = []
    for n in ("a", "b"):
        e = crear_motor(f"sqlite:///{(tmp_path / (n + '.db')).as_posix()}")
        Base.metadata.create_all(e)
        with sessionmaker(bind=e)() as s:
            res.append(sembrar(s, cipher, **kw))
        e.dispose()
    assert res[0] == res[1]


def test_sembrar_con_menos_de_30_dias(db_session, cipher):
    sembrar(db_session, cipher, semilla=1, fin=date(2026, 3, 31), dias=20, n_clientes=10)
