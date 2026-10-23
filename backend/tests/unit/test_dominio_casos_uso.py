from datetime import datetime

import pytest

from app.application.clientes import ServicioClientes, enmascarar_email, enmascarar_telefono
from app.application.inventario import ServicioInventario
from app.application.kpis import ServicioKpis
from app.application.productos import ServicioProductos
from app.application.ventas import ServicioVentas
from app.domain.entities import Producto
from app.domain.errors import Conflicto, Duplicado, NoEncontrado, StockInsuficiente, ValidacionError
from tests.unit.fakes import (FakeCustomerRepo, FakeInventoryRepo, FakeKpiRepo, FakeProductRepo,
                              FakeSaleRepo, FakeTx)


class CipherFalso:
    def cifrar(self, t):
        return None if not t else "enc:" + t

    def descifrar(self, t):
        return None if not t else t.removeprefix("enc:")


@pytest.fixture
def ctx():
    prods = FakeProductRepo([Producto("A1", "Cafe", 1000, "Bebidas", 400, stock=10),
                             Producto("B1", "Pan", 500, "Panaderia", 200, stock=5)])
    inv, tx, cli, ventas = FakeInventoryRepo(), FakeTx(), FakeCustomerRepo(), FakeSaleRepo()
    return dict(prods=prods, inv=inv, tx=tx, cli=cli, ventas=ventas,
                svc_v=ServicioVentas(ventas, prods, cli, inv, tx),
                svc_p=ServicioProductos(prods, inv, tx),
                svc_i=ServicioInventario(inv, prods, tx),
                svc_c=ServicioClientes(cli, CipherFalso(), tx))


# ---- Productos
def test_crear_producto_normaliza_sku_y_registra_inventario_inicial(ctx):
    p = ctx["svc_p"].crear(" x-1 ", "Nuevo", 100, stock=7)
    assert p.sku == "X-1"
    movs = ctx["inv"].data
    assert len(movs) == 1 and movs[0].movement_type == "IN" and movs[0].quantity == 7
    assert ctx["tx"].commits == 1


def test_crear_producto_sin_stock_no_genera_movimiento(ctx):
    ctx["svc_p"].crear("X-2", "Nuevo", 100)
    assert ctx["inv"].data == []


def test_crear_producto_duplicado(ctx):
    with pytest.raises(Duplicado):
        ctx["svc_p"].crear("a1", "Otro", 10)


@pytest.mark.parametrize("kw", [dict(unit_price=0), dict(unit_price=-1), dict(unit_cost=-1), dict(stock=-1)])
def test_crear_producto_validaciones(ctx, kw):
    base = dict(sku="Z", name="n", unit_price=10)
    base.update(kw)
    with pytest.raises(ValidacionError):
        ctx["svc_p"].crear(**base)


def test_crear_producto_sku_vacio(ctx):
    with pytest.raises(ValidacionError):
        ctx["svc_p"].crear("  ", "n", 10)


def test_actualizar_ignora_campos_no_editables(ctx):
    p = ctx["svc_p"].actualizar(1, {"name": "Nuevo", "stock": 999, "sku": "HACK"})
    assert p.name == "Nuevo" and p.stock == 10 and p.sku == "A1"


def test_actualizar_precio_invalido(ctx):
    with pytest.raises(ValidacionError):
        ctx["svc_p"].actualizar(1, {"unit_price": 0})


def test_obtener_inexistente(ctx):
    with pytest.raises(NoEncontrado):
        ctx["svc_p"].obtener(99)


def test_desactivar_es_baja_logica(ctx):
    ctx["svc_p"].desactivar(1)
    assert ctx["prods"].data[1].is_active is False
    assert 1 in ctx["prods"].data


# ---- Ventas
def test_venta_descuenta_stock_y_crea_out(ctx):
    v = ctx["svc_v"].registrar([(1, 3), (2, 2)], "efectivo")
    assert v.total_amount == 4000.0 and v.payment_method == "EFECTIVO"
    assert ctx["prods"].data[1].stock == 7 and ctx["prods"].data[2].stock == 3
    outs = [m for m in ctx["inv"].data if m.movement_type == "OUT"]
    assert {(m.product_id, m.quantity) for m in outs} == {(1, 3), (2, 2)}
    assert all(m.reason == f"Venta #{v.id}" for m in outs)
    assert ctx["tx"].commits == 1


def test_venta_agrupa_items_repetidos(ctx):
    v = ctx["svc_v"].registrar([(1, 2), (1, 3)], "NEQUI")
    assert len(v.items) == 1 and v.items[0].quantity == 5


def test_venta_stock_insuficiente_sin_efectos(ctx):
    with pytest.raises(StockInsuficiente):
        ctx["svc_v"].registrar([(1, 2), (2, 99)], "EFECTIVO")
    assert ctx["prods"].data[1].stock == 10 and ctx["prods"].data[2].stock == 5
    assert ctx["inv"].data == [] and ctx["ventas"].data == {}


def test_venta_exacta_deja_stock_cero(ctx):
    ctx["svc_v"].registrar([(2, 5)], "TARJETA")
    assert ctx["prods"].data[2].stock == 0


def test_venta_rollback_si_falla_ajuste(ctx, monkeypatch):
    monkeypatch.setattr(ctx["prods"], "ajustar_stock", lambda i, d: False)
    with pytest.raises(StockInsuficiente):
        ctx["svc_v"].registrar([(1, 1)], "EFECTIVO")
    assert ctx["tx"].rollbacks == 1 and ctx["tx"].commits == 0


@pytest.mark.parametrize("items,medio,exc", [
    ([], "EFECTIVO", ValidacionError),
    ([(1, 1)], "BITCOIN", ValidacionError),
    ([(1, 0)], "EFECTIVO", ValidacionError),
    ([(99, 1)], "EFECTIVO", NoEncontrado),
])
def test_venta_validaciones(ctx, items, medio, exc):
    with pytest.raises(exc):
        ctx["svc_v"].registrar(items, medio)


def test_venta_producto_inactivo(ctx):
    ctx["prods"].data[1].is_active = False
    with pytest.raises(ValidacionError):
        ctx["svc_v"].registrar([(1, 1)], "EFECTIVO")


def test_venta_cliente_inexistente(ctx):
    with pytest.raises(NoEncontrado):
        ctx["svc_v"].registrar([(1, 1)], "EFECTIVO", customer_id=42)


def test_venta_obtener_inexistente(ctx):
    with pytest.raises(NoEncontrado):
        ctx["svc_v"].obtener(5)


# ---- Inventario
def test_inventario_in_out_merma(ctx):
    s = ctx["svc_i"]
    s.registrar(1, "in", 5)
    assert ctx["prods"].data[1].stock == 15
    s.registrar(1, "OUT", 3)
    s.registrar(1, "MERMA", 2, "vencido")
    assert ctx["prods"].data[1].stock == 10
    assert len(ctx["inv"].data) == 3


def test_inventario_out_excede_stock(ctx):
    with pytest.raises(StockInsuficiente):
        ctx["svc_i"].registrar(2, "OUT", 6)
    assert ctx["inv"].data == [] and ctx["tx"].rollbacks == 1


@pytest.mark.parametrize("tipo,cant", [("XX", 1), ("IN", 0)])
def test_inventario_validaciones(ctx, tipo, cant):
    with pytest.raises(ValidacionError):
        ctx["svc_i"].registrar(1, tipo, cant)


def test_inventario_producto_inexistente(ctx):
    with pytest.raises(NoEncontrado):
        ctx["svc_i"].registrar(77, "IN", 1)


def test_stock_bajo_ordenado_y_solo_activos(ctx):
    ctx["prods"].crear(Producto("C1", "Inactivo", 10, stock=0, is_active=False))
    assert [p.sku for p in ctx["svc_i"].stock_bajo(umbral=5)] == ["B1"]
    assert [p.sku for p in ctx["svc_i"].stock_bajo(umbral=10)] == ["B1", "A1"]


# ---- Clientes
def test_enmascarado():
    assert enmascarar_email("juan@x.com") == "j***@x.com"
    assert enmascarar_email("sinarroba") == "***"
    assert enmascarar_email(None) is None
    assert enmascarar_telefono("3001234567") == "*******567"
    assert enmascarar_telefono(None) is None


def test_cliente_pii_cifrada_y_enmascarada(ctx):
    v = ctx["svc_c"].crear("Ana", "Perez", "ana@x.com", "3001234567")
    assert v.email == "a***@x.com" and v.revelado is False
    assert ctx["cli"].data[v.id].encrypted_email == "enc:ana@x.com"
    assert ctx["svc_c"].obtener(v.id, revelar=True).email == "ana@x.com"


def test_cliente_validaciones(ctx):
    with pytest.raises(ValidacionError):
        ctx["svc_c"].crear(" ", "x")
    with pytest.raises(ValidacionError):
        ctx["svc_c"].crear("a", "b", email="malo")


def test_cliente_eliminar_con_ventas_conflicto(ctx):
    c = ctx["svc_c"].crear("A", "B")
    ctx["cli"].con_ventas.add(c.id)
    with pytest.raises(Conflicto):
        ctx["svc_c"].eliminar(c.id)
    ctx["cli"].con_ventas.clear()
    ctx["svc_c"].eliminar(c.id)
    with pytest.raises(NoEncontrado):
        ctx["svc_c"].obtener(c.id)


def test_cliente_actualizar_email_vacio_lo_borra(ctx):
    c = ctx["svc_c"].crear("A", "B", "a@b.com")
    v = ctx["svc_c"].actualizar(c.id, email="", revelar=True)
    assert v.email is None


# ---- KPIs
def test_kpis_calculos():
    repo = FakeKpiRepo({"total_ventas": 10000.0, "n_ventas": 4, "costo_vendido": 6000.0, "unidades": 9},
                       inv=3000.0, bajo=2)
    r = ServicioKpis(repo).resumen(dias=30, ahora=datetime(2026, 1, 31))
    assert r["ticket_promedio"] == 2500.0
    assert r["margen"] == 4000.0 and r["margen_pct"] == 40.0
    assert r["rotacion"] == 2.0 and r["rotacion_anual"] == round(2.0 * 365 / 30, 3)
    assert r["productos_bajo_stock"] == 2 and r["unidades_vendidas"] == 9
    assert (r["hasta"] - r["desde"]).days == 30


def test_kpis_sin_ventas_ni_inventario_no_divide_por_cero():
    r = ServicioKpis(FakeKpiRepo()).resumen()
    assert r["ticket_promedio"] == 0.0 and r["margen_pct"] == 0.0 and r["rotacion"] == 0.0


@pytest.mark.parametrize("dias", [0, -1, 3651])
def test_kpis_dias_invalidos(dias):
    with pytest.raises(ValidacionError):
        ServicioKpis(FakeKpiRepo()).resumen(dias=dias)
