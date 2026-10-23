"""Repositorios falsos en memoria que implementan los Protocol de app.domain.ports."""
from copy import deepcopy
from dataclasses import replace
from datetime import datetime

from app.domain.entities import Cliente, MovimientoInventario, Producto, Venta


class FakeTx:
    def __init__(self):
        self.commits = 0
        self.rollbacks = 0

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1


class FakeProductRepo:
    def __init__(self, productos=()):
        self.data: dict[int, Producto] = {}
        self._seq = 0
        for p in productos:
            self.crear(p)

    def listar(self, q=None, categoria=None, solo_activos=False, limit=100, offset=0):
        r = list(self.data.values())
        if q:
            r = [p for p in r if q.lower() in p.name.lower() or q.lower() in p.sku.lower()]
        if categoria:
            r = [p for p in r if p.category == categoria]
        if solo_activos:
            r = [p for p in r if p.is_active]
        return r[offset:offset + limit]

    def obtener(self, id):
        return self.data.get(id)

    def obtener_por_sku(self, sku):
        return next((p for p in self.data.values() if p.sku == sku), None)

    def crear(self, p):
        self._seq += 1
        p = replace(p, id=self._seq)
        self.data[p.id] = p
        return p

    def actualizar(self, id, cambios):
        p = self.data[id]
        for k, v in cambios.items():
            setattr(p, k, v)
        return p

    def ajustar_stock(self, id, delta):
        p = self.data[id]
        if p.stock + delta < 0:
            return False
        p.stock += delta
        return True

    def categorias(self):
        return sorted({p.category for p in self.data.values() if p.category})


class FakeCustomerRepo:
    def __init__(self):
        self.data: dict[int, Cliente] = {}
        self._seq = 0
        self.con_ventas: set[int] = set()

    def listar(self, q=None, limit=100, offset=0):
        return list(self.data.values())[offset:offset + limit]

    def obtener(self, id):
        return self.data.get(id)

    def crear(self, c):
        self._seq += 1
        c = replace(c, id=self._seq)
        self.data[c.id] = c
        return c

    def actualizar(self, id, cambios):
        c = self.data[id]
        for k, v in cambios.items():
            setattr(c, k, v)
        return c

    def eliminar(self, id):
        del self.data[id]

    def tiene_ventas(self, id):
        return id in self.con_ventas


class FakeSaleRepo:
    def __init__(self):
        self.data: dict[int, Venta] = {}
        self._seq = 0

    def crear(self, v):
        self._seq += 1
        v = deepcopy(v)
        v.id = self._seq
        self.data[v.id] = v
        return v

    def obtener(self, id):
        return self.data.get(id)

    def listar(self, desde=None, hasta=None, customer_id=None, limit=50, offset=0):
        r = [v for v in self.data.values() if customer_id is None or v.customer_id == customer_id]
        return r[offset:offset + limit]


class FakeInventoryRepo:
    def __init__(self):
        self.data: list[MovimientoInventario] = []

    def registrar(self, mov):
        mov = replace(mov, id=len(self.data) + 1, created_at=mov.created_at or datetime.now())
        self.data.append(mov)
        return mov

    def listar(self, product_id=None, tipo=None, limit=100, offset=0):
        r = [m for m in self.data if (product_id is None or m.product_id == product_id)
             and (tipo is None or m.movement_type == tipo)]
        return r[offset:offset + limit]


class FakeKpiRepo:
    def __init__(self, totales=None, inv=0.0, bajo=0):
        self._t = totales or {"total_ventas": 0.0, "n_ventas": 0, "costo_vendido": 0.0, "unidades": 0}
        self._inv = inv
        self._bajo = bajo

    def totales(self, desde, hasta):
        return self._t

    def serie_diaria(self, desde, hasta):
        return []

    def top_productos(self, desde, hasta, limit):
        return []

    def por_categoria(self, desde, hasta):
        return []

    def valor_inventario(self):
        return self._inv

    def contar_bajo_stock(self, umbral):
        return self._bajo
