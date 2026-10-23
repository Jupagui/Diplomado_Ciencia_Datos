"""Kardex y ajustes manuales de inventario."""
from app.domain.entities import TIPOS_MOVIMIENTO, MovimientoInventario, Producto
from app.domain.errors import NoEncontrado, StockInsuficiente, ValidacionError
from app.domain.ports import InventoryRepo, ProductRepo, Transaccion


class ServicioInventario:
    def __init__(self, inventario: InventoryRepo, productos: ProductRepo, tx: Transaccion):
        self.inventario = inventario
        self.productos = productos
        self.tx = tx

    def listar(self, product_id=None, tipo=None, limit=100, offset=0) -> list[MovimientoInventario]:
        return self.inventario.listar(product_id, tipo, limit, offset)

    def registrar(self, product_id: int, movement_type: str, quantity: int,
                  reason: str | None = None) -> MovimientoInventario:
        tipo = movement_type.strip().upper()
        if tipo not in TIPOS_MOVIMIENTO:
            raise ValidacionError(f"Tipo inválido. Use: {', '.join(TIPOS_MOVIMIENTO)}")
        if quantity <= 0:
            raise ValidacionError("La cantidad debe ser mayor que 0")
        p = self.productos.obtener(product_id)
        if p is None:
            raise NoEncontrado(f"Producto {product_id} no existe")
        delta = quantity if tipo == "IN" else -quantity
        try:
            if not self.productos.ajustar_stock(product_id, delta):
                raise StockInsuficiente(f"Stock insuficiente de {p.name}: disponible {p.stock}")
            mov = self.inventario.registrar(MovimientoInventario(product_id, tipo, quantity, reason))
            self.tx.commit()
        except Exception:
            self.tx.rollback()
            raise
        return mov

    def stock_bajo(self, umbral: int = 10) -> list[Producto]:
        return sorted((p for p in self.productos.listar(solo_activos=True, limit=10000) if p.stock <= umbral),
                      key=lambda p: p.stock)
