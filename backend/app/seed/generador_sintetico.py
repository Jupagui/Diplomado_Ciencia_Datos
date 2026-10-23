"""Generador de datos sintéticos reproducible (semilla fija).

Crea ~40 productos, ~300 clientes (PII cifrada) y 12 meses de ventas con:
- estacionalidad semanal (viernes/sábado fuertes) y mensual (diciembre alto, enero bajo),
- festivos de Colombia (librería `holidays`),
- combos frecuentes de productos (para que Apriori encuentre reglas),
- movimientos de inventario IN/OUT coherentes: stock final = suma(IN) - suma(OUT).
"""
import math
import random
import unicodedata
from datetime import date, datetime, time, timedelta

import holidays
from sqlalchemy import func, insert, select
from sqlalchemy.orm import Session

from app.adapters.outbound.persistence import models as m
from app.domain.entities import MEDIOS_PAGO
from app.domain.ports import CipherPort

SEMILLA = 42

# (sku, nombre, categoría, precio COP, costo COP, popularidad, perecedero)
CATALOGO = [
    ("CAF-001", "Tinto", "Bebidas calientes", 2500, 600, 10, True),
    ("CAF-002", "Café americano", "Bebidas calientes", 4500, 1100, 8, True),
    ("CAF-003", "Cappuccino", "Bebidas calientes", 6500, 1900, 6, True),
    ("CAF-004", "Latte", "Bebidas calientes", 7000, 2100, 5, True),
    ("CAF-005", "Chocolate caliente", "Bebidas calientes", 6000, 1800, 3, True),
    ("CAF-006", "Aromática", "Bebidas calientes", 3000, 500, 2, True),
    ("BEB-001", "Agua botella 600ml", "Bebidas frías", 2500, 1200, 7, False),
    ("BEB-002", "Gaseosa 350ml", "Bebidas frías", 3000, 1700, 7, False),
    ("BEB-003", "Jugo en caja", "Bebidas frías", 3500, 2000, 5, False),
    ("BEB-004", "Té frío", "Bebidas frías", 3800, 1800, 4, False),
    ("BEB-005", "Limonada natural", "Bebidas frías", 5000, 1500, 4, True),
    ("BEB-006", "Cerveza", "Bebidas frías", 4500, 2800, 3, False),
    ("BEB-007", "Café frío", "Bebidas frías", 7500, 2300, 3, True),
    ("PAN-001", "Croissant", "Panadería", 4500, 1800, 6, True),
    ("PAN-002", "Pan de bono", "Panadería", 2500, 900, 7, True),
    ("PAN-003", "Almojábana", "Panadería", 2500, 950, 6, True),
    ("PAN-004", "Pan tajado", "Panadería", 5500, 3800, 3, True),
    ("PAN-005", "Torta porción", "Panadería", 6000, 2400, 4, True),
    ("PAN-006", "Empanada", "Panadería", 3000, 1200, 6, True),
    ("PAN-007", "Sándwich jamón y queso", "Panadería", 8500, 3600, 4, True),
    ("SNK-001", "Papas fritas", "Snacks", 2800, 1700, 6, False),
    ("SNK-002", "Galletas", "Snacks", 1800, 1000, 5, False),
    ("SNK-003", "Chocolatina", "Snacks", 2200, 1300, 5, False),
    ("SNK-004", "Maní", "Snacks", 1500, 800, 4, False),
    ("SNK-005", "Chicles", "Snacks", 1000, 500, 4, False),
    ("SNK-006", "Barra de cereal", "Snacks", 2800, 1500, 3, False),
    ("LAC-001", "Leche 1L", "Lácteos y huevos", 4800, 3600, 5, True),
    ("LAC-002", "Yogurt", "Lácteos y huevos", 3500, 2300, 4, True),
    ("LAC-003", "Queso campesino", "Lácteos y huevos", 7000, 4800, 3, True),
    ("LAC-004", "Huevos x12", "Lácteos y huevos", 12000, 9200, 3, True),
    ("LAC-005", "Mantequilla", "Lácteos y huevos", 5500, 4000, 2, True),
    ("ABA-001", "Arroz 1kg", "Abarrotes", 4200, 3300, 3, False),
    ("ABA-002", "Azúcar 1kg", "Abarrotes", 4000, 3000, 3, False),
    ("ABA-003", "Aceite 1L", "Abarrotes", 11000, 8600, 2, False),
    ("ABA-004", "Café molido 250g", "Abarrotes", 9500, 6500, 2, False),
    ("ABA-005", "Panela", "Abarrotes", 3500, 2600, 2, False),
    ("ABA-006", "Pasta 500g", "Abarrotes", 3200, 2300, 2, False),
    ("ASE-001", "Jabón de baño", "Aseo", 2800, 1800, 2, False),
    ("ASE-002", "Detergente 1kg", "Aseo", 9500, 7000, 1.5, False),
    ("ASE-003", "Papel higiénico x4", "Aseo", 7500, 5200, 2, False),
    ("ASE-004", "Crema dental", "Aseo", 5500, 3700, 2, False),
]

# Combos frecuentes (por SKU): se compran juntos con alta probabilidad
COMBOS = [
    ("CAF-002", "PAN-001"), ("CAF-001", "PAN-002"), ("CAF-003", "PAN-005"), ("CAF-004", "PAN-001"),
    ("CAF-001", "PAN-003"), ("SNK-001", "BEB-002"), ("SNK-001", "BEB-006"), ("PAN-007", "BEB-003"),
    ("PAN-006", "BEB-002"), ("ABA-001", "ABA-003"), ("ABA-002", "ABA-004"), ("PAN-004", "LAC-005", "LAC-003"),
    ("LAC-001", "SNK-002"), ("BEB-007", "PAN-007"),
]

# Factor de demanda por día de la semana (0 = lunes)
FACTOR_SEMANA = [0.85, 0.85, 0.90, 0.95, 1.20, 1.35, 1.00]
# Factor por mes
FACTOR_MES = {1: 0.85, 2: 0.90, 3: 0.95, 4: 1.00, 5: 1.05, 6: 1.05, 7: 1.00, 8: 0.95,
              9: 1.00, 10: 1.05, 11: 1.15, 12: 1.35}
# Estacionalidad por producto: {sku: {mes: factor}}
ESTACIONAL = {"CAF-005": {11: 1.6, 12: 2.2, 1: 1.3}, "BEB-005": {2: 1.5, 3: 1.4, 12: 1.3},
              "BEB-006": {12: 1.8}, "PAN-005": {12: 1.5, 5: 1.3}}
FIN_DE_SEMANA_FUERTE = {"BEB-006": 2.0, "SNK-001": 1.4, "BEB-002": 1.3}

NOMBRES = ["Juan", "María", "Carlos", "Ana", "Luis", "Laura", "Andrés", "Camila", "Santiago", "Valentina",
           "Felipe", "Daniela", "Sebastián", "Paula", "Diego", "Natalia", "Mateo", "Sofía", "Julián", "Isabella",
           "David", "Carolina", "Esteban", "Juliana", "Nicolás", "Alejandra", "Jorge", "Marcela", "Camilo", "Lucía"]
APELLIDOS = ["García", "Rodríguez", "Martínez", "López", "González", "Pérez", "Sánchez", "Ramírez", "Torres",
             "Díaz", "Vargas", "Castro", "Rojas", "Moreno", "Jiménez", "Ortiz", "Gómez", "Herrera", "Medina",
             "Cardona", "Quintero", "Mejía", "Restrepo", "Zapata", "Arango"]


def _ascii(texto: str) -> str:
    return unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode().lower()


def base_vacia(session: Session) -> bool:
    return session.scalar(select(func.count(m.ProductModel.id))) == 0


def sembrar(session: Session, cipher: CipherPort, semilla: int = SEMILLA, fin: date | None = None,
            dias: int = 365, n_clientes: int = 300) -> dict[str, int]:
    """Inserta catálogo, clientes, ventas y kardex. Asume tablas vacías. Devuelve conteos."""
    rng = random.Random(semilla)
    fin = fin or date.today()
    inicio = fin - timedelta(days=dias - 1)
    ahora = datetime.now()
    festivos = holidays.Colombia(years=range(inicio.year, fin.year + 1))

    # ---- Productos ----
    prods = []
    for i, (sku, nombre, cat, precio, costo, pop, perecedero) in enumerate(CATALOGO, start=1):
        objetivo = max(40, int(pop * 12))
        prods.append({"id": i, "sku": sku, "name": nombre, "category": cat, "unit_price": precio,
                      "unit_cost": costo, "pop": pop, "perecedero": perecedero,
                      "objetivo": objetivo, "reorden": int(objetivo * 0.3)})
    id_por_sku = {p["sku"]: p["id"] for p in prods}
    por_id = {p["id"]: p for p in prods}
    stock = {p["id"]: 0 for p in prods}

    # ---- Clientes ----
    clientes = []
    for i in range(1, n_clientes + 1):
        nom, ape = rng.choice(NOMBRES), rng.choice(APELLIDOS)
        alta = inicio - timedelta(days=rng.randint(1, 200)) if rng.random() < 0.7 \
            else inicio + timedelta(days=rng.randint(0, max(0, dias - 30)))
        baja = fin + timedelta(days=1)
        if rng.random() < 0.2:  # clientes que dejan de comprar (churn) para dar variedad a RFM
            baja = inicio + timedelta(days=rng.randint(dias // 3, max(dias // 3, dias - 20)))
        clientes.append({
            "id": i, "first_name": nom, "last_name": ape,
            "encrypted_email": cipher.cifrar(f"{_ascii(nom)}.{_ascii(ape)}{i}@example.com"),
            "encrypted_phone": cipher.cifrar("3" + "".join(str(rng.randint(0, 9)) for _ in range(9))),
            "created_at": datetime.combine(alta, time(9, 0)), "_alta": alta, "_baja": baja,
            "_peso": min(rng.paretovariate(1.4), 25.0),
        })
    pesos_cli = [c["_peso"] for c in clientes]

    ventas, items, movs = [], [], []
    id_venta = 0

    def mov(pid, tipo, cant, motivo, ts):
        movs.append({"product_id": pid, "movement_type": tipo, "quantity": cant, "reason": motivo,
                     "created_at": ts})

    # Inventario inicial
    ts0 = datetime.combine(inicio - timedelta(days=1), time(6, 0))
    for p in prods:
        stock[p["id"]] = p["objetivo"]
        mov(p["id"], "IN", p["objetivo"], "Inventario inicial", ts0)

    for k in range(dias):
        dia = inicio + timedelta(days=k)
        # Reposición de proveedor a las 06:00
        for p in prods:
            if stock[p["id"]] < p["reorden"]:
                cant = p["objetivo"] - stock[p["id"]]
                stock[p["id"]] += cant
                mov(p["id"], "IN", cant, "Reposición proveedor", datetime.combine(dia, time(6, 0)))

        # Mermas ocasionales en perecederos
        if rng.random() < 0.15:
            p = rng.choice([x for x in prods if x["perecedero"]])
            cant = rng.randint(1, 3)
            if stock[p["id"]] >= cant:
                stock[p["id"]] -= cant
                mov(p["id"], "OUT", cant, "Merma: producto vencido o dañado",
                    datetime.combine(dia, time(21, rng.randint(0, 30))))

        # Demanda del día
        lam = 24 * FACTOR_SEMANA[dia.weekday()] * FACTOR_MES[dia.month] * (1 + 0.15 * k / dias)
        if dia in festivos:
            lam *= 1.25
        n_tx = max(0, round(rng.gauss(lam, math.sqrt(lam))))
        fin_semana = dia.weekday() >= 4
        pesos_prod = []
        for p in prods:
            w = p["pop"] * ESTACIONAL.get(p["sku"], {}).get(dia.month, 1.0)
            if fin_semana:
                w *= FIN_DE_SEMANA_FUERTE.get(p["sku"], 1.0)
            pesos_prod.append(w)

        horas = sorted(rng.choices(range(7, 21), weights=[3, 5, 4, 3, 5, 6, 4, 3, 3, 4, 5, 4, 2, 1], k=n_tx))
        for hora in horas:
            ts = datetime.combine(dia, time(hora, rng.randint(0, 59), rng.randint(0, 59)))
            if ts > ahora:  # no generar ventas en el futuro
                continue
            # Armar canasta
            pids: list[int] = []
            if rng.random() < 0.5:
                combo = rng.choice(COMBOS)
                pids.extend(id_por_sku[s] for s in combo)
                if rng.random() < 0.3:
                    pids.append(rng.choices(prods, weights=pesos_prod)[0]["id"])
            else:
                pids.extend(p["id"] for p in rng.choices(prods, weights=pesos_prod, k=rng.choice([1, 1, 2, 3])))
            canasta: dict[int, int] = {}
            for pid in pids:
                cant = rng.choices([1, 2, 3], weights=[80, 15, 5])[0]
                cant = min(cant, stock[pid])
                if cant > 0:
                    canasta[pid] = canasta.get(pid, 0) + cant
            for pid in list(canasta):  # una unidad no puede exceder el stock restante
                canasta[pid] = min(canasta[pid], stock[pid])
            canasta = {pid: c for pid, c in canasta.items() if c > 0}
            if not canasta:
                continue

            # Cliente (70% identificado)
            cliente_id = None
            if rng.random() < 0.7:
                for _ in range(5):
                    c = rng.choices(clientes, weights=pesos_cli)[0]
                    if c["_alta"] <= dia < c["_baja"]:
                        cliente_id = c["id"]
                        break

            id_venta += 1
            total = 0.0
            for pid, cant in canasta.items():
                p = por_id[pid]
                sub = float(p["unit_price"] * cant)
                total += sub
                stock[pid] -= cant
                items.append({"sale_id": id_venta, "product_id": pid, "quantity": cant,
                              "unit_price": p["unit_price"], "subtotal": sub})
                mov(pid, "OUT", cant, f"Venta #{id_venta}", ts)
            ventas.append({"id": id_venta, "customer_id": cliente_id, "total_amount": total,
                           "payment_method": rng.choices(MEDIOS_PAGO, weights=[45, 25, 20, 10])[0],
                           "status": "COMPLETED", "created_at": ts})

    # ---- Inserción masiva (ids explícitos; la base está vacía) ----
    session.execute(insert(m.ProductModel), [
        {"id": p["id"], "sku": p["sku"], "name": p["name"], "category": p["category"],
         "unit_price": p["unit_price"], "unit_cost": p["unit_cost"], "stock": stock[p["id"]],
         "is_active": True, "created_at": datetime.combine(inicio - timedelta(days=2), time(8, 0))}
        for p in prods])
    session.execute(insert(m.CustomerModel), [{k: v for k, v in c.items() if not k.startswith("_")} for c in clientes])
    if ventas:
        session.execute(insert(m.SaleModel), ventas)
        session.execute(insert(m.SaleItemModel), items)
    movs.sort(key=lambda x: x["created_at"])
    session.execute(insert(m.InventoryMovementModel), movs)
    session.commit()
    return {"productos": len(prods), "clientes": len(clientes), "ventas": len(ventas),
            "items": len(items), "movimientos": len(movs)}
