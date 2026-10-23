from datetime import datetime

from pydantic import BaseModel


class TopProducto(BaseModel):
    product_id: int
    name: str
    category: str | None
    unidades: int
    ingresos: float


class VentaCategoria(BaseModel):
    category: str
    unidades: int
    ingresos: float


class PuntoSerie(BaseModel):
    fecha: str
    total: float
    n_ventas: int


class ResumenKpis(BaseModel):
    dias: int
    desde: datetime
    hasta: datetime
    total_ventas: float
    n_ventas: int
    unidades_vendidas: int
    ticket_promedio: float
    costo_vendido: float
    margen: float
    margen_pct: float
    valor_inventario: float
    rotacion: float
    rotacion_anual: float
    productos_bajo_stock: int
    top_productos: list[TopProducto]
    ventas_por_categoria: list[VentaCategoria]
    serie_diaria: list[PuntoSerie]
