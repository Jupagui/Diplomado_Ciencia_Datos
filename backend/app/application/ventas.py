"""Registro transaccional de ventas: valida stock, descuenta y genera el movimiento OUT."""
from datetime import datetime

from app.domain.entities import MEDIOS_PAGO, ItemVenta, MovimientoInventario, Venta
from app.domain.errors import NoEncontrado, StockInsuficiente, ValidacionError
from app.domain.ports import CustomerRepo, InventoryRepo, ProductRepo, SaleRepo, Transaccion


class ServicioVentas:
    def __init__(self, ventas: SaleRepo, productos: ProductRepo, clientes: CustomerRepo,
                 inventario: InventoryRepo, tx: Transaccion):
        self.ventas = ventas
        self.productos = productos
        self.clientes = clientes
        self.inventario = inventario
        self.tx = tx

    def registrar(self, items: list[tuple[int, int]], payment_method: str,
                  customer_id: int | None = None) -> Venta:
        medio = payment_method.strip().upper()
        if medio not in MEDIOS_PAGO:
            raise ValidacionError(f"Medio de pago inválido. Use: {', '.join(MEDIOS_PAGO)}")
        if not items:
            raise ValidacionError("La venta debe tener al menos un ítem")
        if customer_id is not None and self.clientes.obtener(customer_id) is None:
            raise NoEncontrado(f"Cliente {customer_id} no existe")

        pedido: dict[int, int] = {}
        for pid, cant in items:
            if cant <= 0:
                raise ValidacionError("La cantidad debe ser mayor que 0")
            pedido[pid] = pedido.get(pid, 0) + cant

        venta = Venta(payment_method=medio, customer_id=customer_id)
        productos = {}
        for pid, cant in pedido.items():
            p = self.productos.obtener(pid)
            if p is None:
                raise NoEncontrado(f"Producto {pid} no existe")
            if not p.is_active:
                raise ValidacionError(f"El producto {p.sku} está inactivo")
            if p.stock < cant:
                raise StockInsuficiente(f"Stock insuficiente de {p.name}: disponible {p.stock}, solicitado {cant}")
            productos[pid] = p
            sub = round(p.unit_price * cant, 2)
            venta.items.append(ItemVenta(pid, cant, p.unit_price, sub, product_name=p.name))
        venta.total_amount = round(sum(i.subtotal for i in venta.items), 2)
        venta.created_at = datetime.now()

        try:
            venta = self.ventas.crear(venta)
            for it in venta.items:
                if not self.productos.ajustar_stock(it.product_id, -it.quantity):
                    raise StockInsuficiente(f"Stock insuficiente de {productos[it.product_id].name}")
                self.inventario.registrar(MovimientoInventario(it.product_id, "OUT", it.quantity,
                                                               f"Venta #{venta.id}", created_at=venta.created_at))
            self.tx.commit()
        except Exception:
            self.tx.rollback()
            raise
        return venta

    def obtener(self, id: int) -> Venta:
        v = self.ventas.obtener(id)
        if v is None:
            raise NoEncontrado(f"Venta {id} no existe")
        return v

    def listar(self, desde=None, hasta=None, customer_id=None, limit=50, offset=0) -> list[Venta]:
        return self.ventas.listar(desde, hasta, customer_id, limit, offset)
