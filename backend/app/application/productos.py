"""Casos de uso de productos."""
from typing import Any

from app.domain.entities import MovimientoInventario, Producto
from app.domain.errors import Duplicado, NoEncontrado, ValidacionError
from app.domain.ports import InventoryRepo, ProductRepo, Transaccion

CAMPOS_EDITABLES = {"name", "category", "unit_price", "unit_cost", "is_active"}


class ServicioProductos:
    def __init__(self, repo: ProductRepo, inventario: InventoryRepo, tx: Transaccion):
        self.repo = repo
        self.inventario = inventario
        self.tx = tx

    def listar(self, q=None, categoria=None, solo_activos=False, limit=100, offset=0) -> list[Producto]:
        return self.repo.listar(q, categoria, solo_activos, limit, offset)

    def categorias(self) -> list[str]:
        return self.repo.categorias()

    def obtener(self, id: int) -> Producto:
        p = self.repo.obtener(id)
        if p is None:
            raise NoEncontrado(f"Producto {id} no existe")
        return p

    def crear(self, sku: str, name: str, unit_price: float, category: str | None = None,
              unit_cost: float = 0.0, stock: int = 0) -> Producto:
        sku = sku.strip().upper()
        if not sku or not name.strip():
            raise ValidacionError("SKU y nombre son obligatorios")
        if unit_price <= 0:
            raise ValidacionError("El precio debe ser mayor que 0")
        if unit_cost < 0 or stock < 0:
            raise ValidacionError("Costo y stock no pueden ser negativos")
        if self.repo.obtener_por_sku(sku):
            raise Duplicado(f"Ya existe un producto con SKU {sku}")
        try:
            p = self.repo.crear(Producto(sku=sku, name=name.strip(), unit_price=unit_price, category=category,
                                         unit_cost=unit_cost, stock=stock))
            if stock > 0:
                self.inventario.registrar(MovimientoInventario(p.id, "IN", stock, "Inventario inicial"))
            self.tx.commit()
        except Exception:
            self.tx.rollback()
            raise
        return p

    def actualizar(self, id: int, cambios: dict[str, Any]) -> Producto:
        self.obtener(id)
        cambios = {k: v for k, v in cambios.items() if k in CAMPOS_EDITABLES and v is not None}
        if "unit_price" in cambios and cambios["unit_price"] <= 0:
            raise ValidacionError("El precio debe ser mayor que 0")
        if "unit_cost" in cambios and cambios["unit_cost"] < 0:
            raise ValidacionError("El costo no puede ser negativo")
        p = self.repo.actualizar(id, cambios)
        self.tx.commit()
        return p

    def desactivar(self, id: int) -> None:
        """Baja lógica: conserva el historial de ventas y kardex."""
        self.obtener(id)
        self.repo.actualizar(id, {"is_active": False})
        self.tx.commit()
