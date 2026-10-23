"""Repositorios SQLAlchemy que implementan los puertos del dominio."""
from datetime import datetime
from typing import Any

from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Session, selectinload

from app.adapters.outbound.persistence import models as m
from app.domain.entities import Cliente, ItemVenta, MovimientoInventario, Producto, Usuario, Venta

COMPLETADA = "COMPLETED"


def _producto(r: m.ProductModel) -> Producto:
    return Producto(sku=r.sku, name=r.name, unit_price=float(r.unit_price), category=r.category,
                    unit_cost=float(r.unit_cost or 0), stock=r.stock, is_active=bool(r.is_active),
                    id=r.id, created_at=r.created_at)


def _cliente(r: m.CustomerModel) -> Cliente:
    return Cliente(r.first_name, r.last_name, r.encrypted_email, r.encrypted_phone, r.id, r.created_at)


def _venta(r: m.SaleModel) -> Venta:
    items = [ItemVenta(i.product_id, i.quantity, float(i.unit_price), float(i.subtotal), i.id, i.sale_id,
                       i.product.name if i.product else None) for i in r.items]
    return Venta(r.payment_method, float(r.total_amount), r.customer_id, r.status, items, r.id, r.created_at)


def _mov(r: m.InventoryMovementModel) -> MovimientoInventario:
    return MovimientoInventario(r.product_id, r.movement_type, r.quantity, r.reason, r.id, r.created_at)


class ProductRepoSQL:
    def __init__(self, s: Session):
        self.s = s

    def listar(self, q=None, categoria=None, solo_activos=False, limit=100, offset=0):
        stmt = select(m.ProductModel)
        if q:
            like = f"%{q}%"
            stmt = stmt.where(m.ProductModel.name.ilike(like) | m.ProductModel.sku.ilike(like))
        if categoria:
            stmt = stmt.where(m.ProductModel.category == categoria)
        if solo_activos:
            stmt = stmt.where(m.ProductModel.is_active.is_(True))
        stmt = stmt.order_by(m.ProductModel.name).limit(limit).offset(offset)
        return [_producto(r) for r in self.s.scalars(stmt)]

    def obtener(self, id):
        r = self.s.get(m.ProductModel, id)
        return _producto(r) if r else None

    def obtener_por_sku(self, sku):
        r = self.s.scalar(select(m.ProductModel).where(m.ProductModel.sku == sku))
        return _producto(r) if r else None

    def crear(self, p: Producto):
        r = m.ProductModel(sku=p.sku, name=p.name, category=p.category, unit_price=p.unit_price,
                           unit_cost=p.unit_cost, stock=p.stock, is_active=p.is_active)
        self.s.add(r)
        self.s.flush()
        return _producto(r)

    def actualizar(self, id, cambios: dict[str, Any]):
        r = self.s.get(m.ProductModel, id)
        for k, v in cambios.items():
            setattr(r, k, v)
        self.s.flush()
        return _producto(r)

    def ajustar_stock(self, id, delta) -> bool:
        """UPDATE atómico: nunca deja el stock negativo."""
        res = self.s.execute(
            update(m.ProductModel)
            .where(m.ProductModel.id == id, m.ProductModel.stock + delta >= 0)
            .values(stock=m.ProductModel.stock + delta)
            .execution_options(synchronize_session="fetch"))
        return res.rowcount > 0

    def categorias(self):
        return list(self.s.scalars(select(m.ProductModel.category).where(m.ProductModel.category.is_not(None))
                                   .distinct().order_by(m.ProductModel.category)))


class CustomerRepoSQL:
    def __init__(self, s: Session):
        self.s = s

    def listar(self, q=None, limit=100, offset=0):
        stmt = select(m.CustomerModel)
        if q:
            like = f"%{q}%"
            stmt = stmt.where(m.CustomerModel.first_name.ilike(like) | m.CustomerModel.last_name.ilike(like))
        stmt = stmt.order_by(m.CustomerModel.id).limit(limit).offset(offset)
        return [_cliente(r) for r in self.s.scalars(stmt)]

    def obtener(self, id):
        r = self.s.get(m.CustomerModel, id)
        return _cliente(r) if r else None

    def crear(self, c: Cliente):
        r = m.CustomerModel(first_name=c.first_name, last_name=c.last_name,
                            encrypted_email=c.encrypted_email, encrypted_phone=c.encrypted_phone)
        self.s.add(r)
        self.s.flush()
        return _cliente(r)

    def actualizar(self, id, cambios):
        r = self.s.get(m.CustomerModel, id)
        for k, v in cambios.items():
            setattr(r, k, v)
        self.s.flush()
        return _cliente(r)

    def eliminar(self, id):
        self.s.execute(delete(m.CustomerModel).where(m.CustomerModel.id == id))

    def tiene_ventas(self, id):
        return self.s.scalar(select(func.count(m.SaleModel.id)).where(m.SaleModel.customer_id == id)) > 0


class SaleRepoSQL:
    def __init__(self, s: Session):
        self.s = s

    def crear(self, v: Venta):
        r = m.SaleModel(customer_id=v.customer_id, total_amount=v.total_amount, payment_method=v.payment_method,
                        status=v.status, created_at=v.created_at or datetime.now())
        r.items = [m.SaleItemModel(product_id=i.product_id, quantity=i.quantity, unit_price=i.unit_price,
                                   subtotal=i.subtotal) for i in v.items]
        self.s.add(r)
        self.s.flush()
        self.s.refresh(r)
        return _venta(r)

    def obtener(self, id):
        r = self.s.scalar(select(m.SaleModel).options(selectinload(m.SaleModel.items).selectinload(
            m.SaleItemModel.product)).where(m.SaleModel.id == id))
        return _venta(r) if r else None

    def listar(self, desde=None, hasta=None, customer_id=None, limit=50, offset=0):
        stmt = select(m.SaleModel).options(selectinload(m.SaleModel.items).selectinload(m.SaleItemModel.product))
        if desde:
            stmt = stmt.where(m.SaleModel.created_at >= desde)
        if hasta:
            stmt = stmt.where(m.SaleModel.created_at <= hasta)
        if customer_id:
            stmt = stmt.where(m.SaleModel.customer_id == customer_id)
        stmt = stmt.order_by(m.SaleModel.created_at.desc(), m.SaleModel.id.desc()).limit(limit).offset(offset)
        return [_venta(r) for r in self.s.scalars(stmt)]


class InventoryRepoSQL:
    def __init__(self, s: Session):
        self.s = s

    def registrar(self, mov: MovimientoInventario):
        r = m.InventoryMovementModel(product_id=mov.product_id, movement_type=mov.movement_type,
                                     quantity=mov.quantity, reason=mov.reason,
                                     created_at=mov.created_at or datetime.now())
        self.s.add(r)
        self.s.flush()
        return _mov(r)

    def listar(self, product_id=None, tipo=None, limit=100, offset=0):
        stmt = select(m.InventoryMovementModel)
        if product_id:
            stmt = stmt.where(m.InventoryMovementModel.product_id == product_id)
        if tipo:
            stmt = stmt.where(m.InventoryMovementModel.movement_type == tipo)
        stmt = stmt.order_by(m.InventoryMovementModel.created_at.desc(), m.InventoryMovementModel.id.desc())
        return [_mov(r) for r in self.s.scalars(stmt.limit(limit).offset(offset))]


class KpiRepoSQL:
    def __init__(self, s: Session):
        self.s = s

    @staticmethod
    def _filtro(desde, hasta):
        return (m.SaleModel.status == COMPLETADA, m.SaleModel.created_at >= desde, m.SaleModel.created_at <= hasta)

    def totales(self, desde, hasta):
        n, total = self.s.execute(select(func.count(m.SaleModel.id), func.coalesce(func.sum(m.SaleModel.total_amount), 0))
                                  .where(*self._filtro(desde, hasta))).one()
        uds, costo = self.s.execute(
            select(func.coalesce(func.sum(m.SaleItemModel.quantity), 0),
                   func.coalesce(func.sum(m.SaleItemModel.quantity * m.ProductModel.unit_cost), 0))
            .join(m.SaleModel, m.SaleModel.id == m.SaleItemModel.sale_id)
            .join(m.ProductModel, m.ProductModel.id == m.SaleItemModel.product_id)
            .where(*self._filtro(desde, hasta))).one()
        return {"n_ventas": n, "total_ventas": float(total), "unidades": float(uds), "costo_vendido": float(costo)}

    def serie_diaria(self, desde, hasta):
        dia = func.date(m.SaleModel.created_at)
        filas = self.s.execute(select(dia, func.sum(m.SaleModel.total_amount), func.count(m.SaleModel.id))
                               .where(*self._filtro(desde, hasta)).group_by(dia).order_by(dia)).all()
        return [{"fecha": f, "total": round(float(t), 2), "n_ventas": n} for f, t, n in filas]

    def top_productos(self, desde, hasta, limit):
        ingresos = func.sum(m.SaleItemModel.subtotal)
        filas = self.s.execute(
            select(m.ProductModel.id, m.ProductModel.name, m.ProductModel.category,
                   func.sum(m.SaleItemModel.quantity), ingresos)
            .join(m.SaleModel, m.SaleModel.id == m.SaleItemModel.sale_id)
            .join(m.ProductModel, m.ProductModel.id == m.SaleItemModel.product_id)
            .where(*self._filtro(desde, hasta)).group_by(m.ProductModel.id).order_by(ingresos.desc()).limit(limit)).all()
        return [{"product_id": i, "name": n, "category": c, "unidades": int(u), "ingresos": round(float(g), 2)}
                for i, n, c, u, g in filas]

    def por_categoria(self, desde, hasta):
        ingresos = func.sum(m.SaleItemModel.subtotal)
        cat = func.coalesce(m.ProductModel.category, "Sin categoría")
        filas = self.s.execute(
            select(cat, func.sum(m.SaleItemModel.quantity), ingresos)
            .join(m.SaleModel, m.SaleModel.id == m.SaleItemModel.sale_id)
            .join(m.ProductModel, m.ProductModel.id == m.SaleItemModel.product_id)
            .where(*self._filtro(desde, hasta)).group_by(cat).order_by(ingresos.desc())).all()
        return [{"category": c, "unidades": int(u), "ingresos": round(float(g), 2)} for c, u, g in filas]

    def valor_inventario(self):
        v = self.s.scalar(select(func.coalesce(func.sum(m.ProductModel.stock * m.ProductModel.unit_cost), 0))
                          .where(m.ProductModel.is_active.is_(True)))
        return float(v)

    def contar_bajo_stock(self, umbral):
        return self.s.scalar(select(func.count(m.ProductModel.id)).where(
            m.ProductModel.is_active.is_(True), m.ProductModel.stock <= umbral))


class UserRepoSQL:
    def __init__(self, s: Session):
        self.s = s

    def obtener_por_username(self, username):
        r = self.s.scalar(select(m.UserModel).where(m.UserModel.username == username))
        return Usuario(r.username, r.password_hash, bool(r.is_admin), r.id) if r else None

    def crear(self, u: Usuario):
        r = m.UserModel(username=u.username, password_hash=u.password_hash, is_admin=u.is_admin)
        self.s.add(r)
        self.s.flush()
        return Usuario(r.username, r.password_hash, bool(r.is_admin), r.id)
