"""KPIs operacionales: ventas, ticket promedio, margen, rotación, top productos y serie diaria."""
from datetime import datetime, timedelta
from typing import Any

from app.domain.errors import ValidacionError
from app.domain.ports import KpiRepo


class ServicioKpis:
    def __init__(self, repo: KpiRepo, umbral_stock_bajo: int = 10):
        self.repo = repo
        self.umbral = umbral_stock_bajo

    def resumen(self, dias: int = 30, top: int = 5, ahora: datetime | None = None) -> dict[str, Any]:
        if dias <= 0 or dias > 3650:
            raise ValidacionError("dias debe estar entre 1 y 3650")
        hasta = ahora or datetime.now()
        desde = hasta - timedelta(days=dias)
        t = self.repo.totales(desde, hasta)
        ventas, n, costo = t["total_ventas"], int(t["n_ventas"]), t["costo_vendido"]
        margen = ventas - costo
        inv = self.repo.valor_inventario()
        rotacion = costo / inv if inv > 0 else 0.0
        return {
            "dias": dias,
            "desde": desde,
            "hasta": hasta,
            "total_ventas": round(ventas, 2),
            "n_ventas": n,
            "unidades_vendidas": int(t["unidades"]),
            "ticket_promedio": round(ventas / n, 2) if n else 0.0,
            "costo_vendido": round(costo, 2),
            "margen": round(margen, 2),
            "margen_pct": round(margen / ventas * 100, 2) if ventas else 0.0,
            "valor_inventario": round(inv, 2),
            "rotacion": round(rotacion, 3),  # veces que se vendió el inventario (a costo) en el periodo
            "rotacion_anual": round(rotacion * 365 / dias, 3),
            "productos_bajo_stock": self.repo.contar_bajo_stock(self.umbral),
            "top_productos": self.repo.top_productos(desde, hasta, top),
            "ventas_por_categoria": self.repo.por_categoria(desde, hasta),
            "serie_diaria": self.repo.serie_diaria(desde, hasta),
        }
