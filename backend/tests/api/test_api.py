import pytest

P = "/api/v1"


# ---- Salud y auth
def test_health_sin_token(client):
    r = client.get(f"{P}/health")
    assert r.status_code == 200 and r.json()["status"] == "ok"


@pytest.mark.parametrize("ruta", ["/products", "/customers", "/sales", "/inventory/movements",
                                  "/inventory/low-stock", "/kpis/resumen", "/auth/me"])
def test_401_sin_token(client, ruta):
    assert client.get(P + ruta).status_code == 401


def test_401_token_invalido(client):
    r = client.get(f"{P}/products", headers={"Authorization": "Bearer basura"})
    assert r.status_code == 401


def test_login_ok(client):
    r = client.post(f"{P}/auth/login", json={"username": "admin", "password": "admin123"})
    assert r.status_code == 200
    j = r.json()
    assert j["token_type"] == "bearer" and j["access_token"] and j["username"] == "admin"
    me = client.get(f"{P}/auth/me", headers={"Authorization": f"Bearer {j['access_token']}"})
    assert me.json() == {"username": "admin"}


@pytest.mark.parametrize("body", [{"username": "admin", "password": "mala"},
                                  {"username": "nadie", "password": "admin123"}])
def test_login_incorrecto(client, body):
    r = client.post(f"{P}/auth/login", json=body)
    assert r.status_code == 401
    assert r.headers.get("www-authenticate") == "Bearer"


def test_login_cuerpo_invalido(client):
    assert client.post(f"{P}/auth/login", json={"username": "a"}).status_code == 422


# ---- Productos
def test_crud_productos_y_baja_logica(client, auth, mk_producto):
    p = mk_producto("CAF-1", "Cafe", 1500, 600, 8)
    assert p["stock"] == 8 and p["is_active"] is True
    pid = p["id"]

    assert client.get(f"{P}/products/{pid}", headers=auth).json()["sku"] == "CAF-1"
    r = client.put(f"{P}/products/{pid}", headers=auth, json={"name": "Cafe grande", "unit_price": 2000})
    assert r.status_code == 200 and r.json()["name"] == "Cafe grande" and r.json()["unit_price"] == 2000
    assert any(x["id"] == pid for x in client.get(f"{P}/products?q=grande", headers=auth).json())
    assert "Bebidas" in client.get(f"{P}/products/categories", headers=auth).json()

    assert client.delete(f"{P}/products/{pid}", headers=auth).status_code == 204
    r = client.get(f"{P}/products/{pid}", headers=auth)
    assert r.status_code == 200 and r.json()["is_active"] is False  # baja lógica: sigue existiendo
    activos = client.get(f"{P}/products?solo_activos=true", headers=auth).json()
    assert pid not in [x["id"] for x in activos]
    assert pid in [x["id"] for x in client.get(f"{P}/products", headers=auth).json()]


def test_producto_sku_duplicado_409(client, auth, mk_producto):
    mk_producto("DUP")
    r = client.post(f"{P}/products", headers=auth, json={"sku": "dup", "name": "x", "unit_price": 10})
    assert r.status_code == 409


@pytest.mark.parametrize("body", [{"sku": "A", "name": "n", "unit_price": 0},
                                  {"sku": "A", "name": "n", "unit_price": 5, "stock": -1},
                                  {"sku": "", "name": "n", "unit_price": 5}])
def test_producto_invalido_422(client, auth, body):
    assert client.post(f"{P}/products", headers=auth, json=body).status_code == 422


def test_producto_inexistente_404(client, auth):
    assert client.get(f"{P}/products/999", headers=auth).status_code == 404
    assert client.put(f"{P}/products/999", headers=auth, json={"name": "x"}).status_code == 404
    assert client.delete(f"{P}/products/999", headers=auth).status_code == 404


def test_producto_inactivo_no_se_vende(client, auth, mk_producto):
    p = mk_producto()
    client.delete(f"{P}/products/{p['id']}", headers=auth)
    r = client.post(f"{P}/sales", headers=auth, json={"items": [{"product_id": p["id"], "quantity": 1}],
                                                      "payment_method": "EFECTIVO"})
    assert r.status_code == 422


# ---- Clientes
def test_clientes_pii_enmascarada_y_revelar(client, auth):
    r = client.post(f"{P}/customers", headers=auth, json={
        "first_name": "Ana", "last_name": "Perez", "email": "ana.perez@example.com", "phone": "3001234567"})
    assert r.status_code == 201
    c = r.json()
    assert c["email"] == "a***@example.com" and c["phone"] == "*******567" and c["revelado"] is False
    cid = c["id"]

    g = client.get(f"{P}/customers/{cid}", headers=auth).json()
    assert g["email"] == "a***@example.com"
    rev = client.get(f"{P}/customers/{cid}?revelar=true", headers=auth).json()
    assert rev["email"] == "ana.perez@example.com" and rev["phone"] == "3001234567" and rev["revelado"] is True
    lst = client.get(f"{P}/customers?revelar=true", headers=auth).json()
    assert lst[0]["email"] == "ana.perez@example.com"
    assert "ana.perez" not in client.get(f"{P}/customers", headers=auth).text


def test_pii_cifrada_en_bd(client, auth, session_factory):
    from app.adapters.outbound.persistence import models as m
    client.post(f"{P}/customers", headers=auth, json={"first_name": "A", "last_name": "B", "email": "x@y.com"})
    with session_factory() as s:
        c = s.query(m.CustomerModel).one()
        assert "x@y.com" not in c.encrypted_email


def test_cliente_actualizar_eliminar(client, auth):
    cid = client.post(f"{P}/customers", headers=auth, json={"first_name": "A", "last_name": "B"}).json()["id"]
    r = client.put(f"{P}/customers/{cid}", headers=auth, json={"first_name": "Zoe", "email": "z@z.com"})
    assert r.status_code == 200 and r.json()["first_name"] == "Zoe" and r.json()["email"] == "z***@z.com"
    assert client.delete(f"{P}/customers/{cid}", headers=auth).status_code == 204
    assert client.get(f"{P}/customers/{cid}", headers=auth).status_code == 404


def test_cliente_email_invalido_422(client, auth):
    r = client.post(f"{P}/customers", headers=auth, json={"first_name": "A", "last_name": "B", "email": "sin"})
    assert r.status_code == 422


def test_cliente_con_ventas_no_se_elimina(client, auth, mk_producto):
    p = mk_producto()
    cid = client.post(f"{P}/customers", headers=auth, json={"first_name": "A", "last_name": "B"}).json()["id"]
    client.post(f"{P}/sales", headers=auth, json={"items": [{"product_id": p["id"], "quantity": 1}],
                                                  "payment_method": "EFECTIVO", "customer_id": cid})
    assert client.delete(f"{P}/customers/{cid}", headers=auth).status_code == 409


# ---- Ventas
def _venta(client, auth, items, medio="EFECTIVO", **kw):
    return client.post(f"{P}/sales", headers=auth, json={
        "items": [{"product_id": i, "quantity": q} for i, q in items], "payment_method": medio, **kw})


def test_venta_descuenta_stock_y_crea_out(client, auth, mk_producto):
    a = mk_producto("A", "Cafe", 1000, 400, 10)
    b = mk_producto("B", "Pan", 500, 200, 5)
    r = _venta(client, auth, [(a["id"], 3), (b["id"], 2)], "nequi")
    assert r.status_code == 201, r.text
    v = r.json()
    assert v["total_amount"] == 4000 and v["status"] == "COMPLETED" and v["payment_method"] == "NEQUI"
    assert len(v["items"]) == 2 and {i["product_name"] for i in v["items"]} == {"Cafe", "Pan"}

    assert client.get(f"{P}/products/{a['id']}", headers=auth).json()["stock"] == 7
    assert client.get(f"{P}/products/{b['id']}", headers=auth).json()["stock"] == 3

    movs = client.get(f"{P}/inventory/movements?product_id={a['id']}&movement_type=out", headers=auth).json()
    assert len(movs) == 1 and movs[0]["quantity"] == 3 and movs[0]["reason"] == f"Venta #{v['id']}"

    assert client.get(f"{P}/sales/{v['id']}", headers=auth).json()["total_amount"] == 4000
    assert [x["id"] for x in client.get(f"{P}/sales", headers=auth).json()] == [v["id"]]


def test_venta_stock_insuficiente_409_sin_efectos_parciales(client, auth, mk_producto):
    a = mk_producto("A", "Cafe", 1000, 400, 10)
    b = mk_producto("B", "Pan", 500, 200, 2)
    r = _venta(client, auth, [(a["id"], 3), (b["id"], 5)])
    assert r.status_code == 409
    assert "Stock insuficiente" in r.json()["detail"]
    assert client.get(f"{P}/products/{a['id']}", headers=auth).json()["stock"] == 10
    assert client.get(f"{P}/products/{b['id']}", headers=auth).json()["stock"] == 2
    assert client.get(f"{P}/sales", headers=auth).json() == []
    assert client.get(f"{P}/inventory/movements?movement_type=OUT", headers=auth).json() == []


def test_venta_sin_efectos_parciales_en_bd(client, auth, mk_producto, session_factory):
    from app.adapters.outbound.persistence import models as m
    a = mk_producto("A", stock=1)
    assert _venta(client, auth, [(a["id"], 2)]).status_code == 409
    with session_factory() as s:
        assert s.query(m.SaleModel).count() == 0 and s.query(m.SaleItemModel).count() == 0


@pytest.mark.parametrize("body,code", [
    ({"items": [], "payment_method": "EFECTIVO"}, 422),
    ({"items": [{"product_id": 1, "quantity": 0}], "payment_method": "EFECTIVO"}, 422),
    ({"items": [{"product_id": 1, "quantity": 1}], "payment_method": "BITCOIN"}, 422),
    ({"items": [{"product_id": 999, "quantity": 1}], "payment_method": "EFECTIVO"}, 404),
])
def test_venta_invalida(client, auth, mk_producto, body, code):
    mk_producto()
    assert client.post(f"{P}/sales", headers=auth, json=body).status_code == code


def test_venta_cliente_inexistente_404(client, auth, mk_producto):
    p = mk_producto()
    assert _venta(client, auth, [(p["id"], 1)], customer_id=999).status_code == 404


def test_venta_agota_stock_y_siguiente_falla(client, auth, mk_producto):
    p = mk_producto(stock=2)
    assert _venta(client, auth, [(p["id"], 2)]).status_code == 201
    assert _venta(client, auth, [(p["id"], 1)]).status_code == 409


def test_sale_404(client, auth):
    assert client.get(f"{P}/sales/999", headers=auth).status_code == 404


# ---- Inventario / kardex
def test_kardex_inicial_y_ajustes(client, auth, mk_producto):
    p = mk_producto(stock=5)
    movs = client.get(f"{P}/inventory/movements?product_id={p['id']}", headers=auth).json()
    assert [(m["movement_type"], m["quantity"]) for m in movs] == [("IN", 5)]

    r = client.post(f"{P}/inventory/movements", headers=auth,
                    json={"product_id": p["id"], "movement_type": "IN", "quantity": 10, "reason": "Compra"})
    assert r.status_code == 201
    client.post(f"{P}/inventory/movements", headers=auth,
                json={"product_id": p["id"], "movement_type": "MERMA", "quantity": 3})
    assert client.get(f"{P}/products/{p['id']}", headers=auth).json()["stock"] == 12

    movs = client.get(f"{P}/inventory/movements?product_id={p['id']}", headers=auth).json()
    saldo = sum(m["quantity"] if m["movement_type"] == "IN" else -m["quantity"] for m in movs)
    assert saldo == 12  # kardex coherente con el stock


def test_kardex_out_excede_stock_409(client, auth, mk_producto):
    p = mk_producto(stock=2)
    r = client.post(f"{P}/inventory/movements", headers=auth,
                    json={"product_id": p["id"], "movement_type": "OUT", "quantity": 3})
    assert r.status_code == 409
    assert client.get(f"{P}/products/{p['id']}", headers=auth).json()["stock"] == 2


@pytest.mark.parametrize("body,code", [
    ({"product_id": 1, "movement_type": "XX", "quantity": 1}, 422),
    ({"product_id": 1, "movement_type": "IN", "quantity": 0}, 422),
    ({"product_id": 999, "movement_type": "IN", "quantity": 1}, 404),
])
def test_kardex_invalido(client, auth, mk_producto, body, code):
    mk_producto()
    assert client.post(f"{P}/inventory/movements", headers=auth, json=body).status_code == code


def test_low_stock(client, auth, mk_producto):
    mk_producto("A", stock=3)
    mk_producto("B", stock=50)
    mk_producto("C", stock=1)
    r = client.get(f"{P}/inventory/low-stock?umbral=10", headers=auth).json()
    assert [p["sku"] for p in r] == ["C", "A"]
    assert client.get(f"{P}/inventory/low-stock?umbral=0", headers=auth).json() == []


# ---- KPIs
def test_kpis_vacio(client, auth):
    r = client.get(f"{P}/kpis/resumen", headers=auth)
    assert r.status_code == 200
    j = r.json()
    assert j["total_ventas"] == 0 and j["n_ventas"] == 0 and j["ticket_promedio"] == 0
    assert j["top_productos"] == [] and j["serie_diaria"] == []


def test_kpis_resumen_con_ventas(client, auth, mk_producto):
    a = mk_producto("A", "Cafe", 1000, 400, 20)
    b = mk_producto("B", "Pan", 500, 200, 20)
    assert _venta(client, auth, [(a["id"], 2), (b["id"], 2)]).status_code == 201   # 3000, costo 1200
    assert _venta(client, auth, [(a["id"], 1)]).status_code == 201                 # 1000, costo 400
    j = client.get(f"{P}/kpis/resumen?dias=7&top=1", headers=auth).json()
    assert j["n_ventas"] == 2 and j["total_ventas"] == 4000
    assert j["ticket_promedio"] == 2000
    assert j["unidades_vendidas"] == 5
    assert j["costo_vendido"] == 1600 and j["margen"] == 2400 and j["margen_pct"] == 60.0
    assert j["valor_inventario"] == 17 * 400 + 18 * 200
    assert j["rotacion"] == pytest.approx(1600 / (17 * 400 + 18 * 200), abs=1e-3)
    assert len(j["top_productos"]) == 1 and j["top_productos"][0]["name"] == "Cafe"
    assert j["top_productos"][0]["unidades"] == 3 and j["top_productos"][0]["ingresos"] == 3000
    assert sum(p["total"] for p in j["serie_diaria"]) == 4000
    assert {c["category"] for c in j["ventas_por_categoria"]} == {"Bebidas"}


def test_kpis_bajo_stock_y_parametros(client, auth, mk_producto):
    mk_producto("A", stock=2)
    assert client.get(f"{P}/kpis/resumen", headers=auth).json()["productos_bajo_stock"] == 1
    assert client.get(f"{P}/kpis/resumen?dias=0", headers=auth).status_code == 422
