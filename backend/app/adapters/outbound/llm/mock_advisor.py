"""Asesor simulado y determinístico: arma el plan solo con las tablas analíticas (sin red ni API key)."""
import json
from typing import Any


def _fmt(n: float) -> str:
    return f"{n:,.0f}".replace(",", ".")


class MockAdvisor:
    modo = "simulado"

    def generar(self, pregunta: str, contexto: dict[str, Any], error_previo: str | None = None) -> str:
        plan = self._plan(pregunta.lower(), contexto)
        return json.dumps(plan, ensure_ascii=False)

    def _plan(self, q: str, c: dict[str, Any]) -> dict[str, Any]:
        k = c.get("kpis_30d", {})
        advertencias = ["Plan generado en modo simulado (sin Gemini): reglas determinísticas sobre las tablas analíticas."]
        if not c.get("hay_datos_analiticos"):
            return {
                "resumen": "Aún no hay resultados analíticos; primero hay que ejecutar el ETL.",
                "acciones": [{
                    "accion": "Ejecutar el ETL desde la página Datos para entrenar los modelos",
                    "justificacion": "Sin pronósticos, reglas ni segmentos no es posible recomendar acciones precisas.",
                    "impacto_estimado": "Habilita recomendaciones de inventario, venta cruzada y fidelización",
                    "riesgo": "bajo",
                    "datos_citados": [f"Ventas últimos 30 días: ${_fmt(k.get('total_ventas', 0))}",
                                      "Tablas analytics_* vacías"]}],
                "advertencias": advertencias}

        acciones: dict[str, dict] = {}

        # 1) Reposición según demanda proyectada vs stock
        riesgo_stock = [d for d in c.get("demanda_7d", []) if d["total_predicho"] > d["stock"] * 0.6]
        riesgo_stock.sort(key=lambda d: d["total_predicho"] / max(d["stock"], 1), reverse=True)
        if riesgo_stock:
            top = riesgo_stock[:3]
            nombres = ", ".join(d["producto"] for d in top)
            acciones["inventario"] = {
                "accion": f"Reponer de inmediato: {nombres}",
                "justificacion": "La demanda proyectada a 7 días consume una parte alta del stock actual y hay riesgo de quiebre.",
                "impacto_estimado": "Evita ventas perdidas por quiebre de stock en la próxima semana",
                "riesgo": "bajo",
                "datos_citados": [f"{d['producto']}: demanda 7d {d['total_predicho']:.0f} u. vs stock {d['stock']} u."
                                  for d in top]}

        # 2) Venta cruzada
        if c.get("reglas_venta_cruzada"):
            r = c["reglas_venta_cruzada"][0]
            acciones["cruzada"] = {
                "accion": f"Crear un combo «{r['antecedent']} + {r['consequent']}» y ubicarlos juntos en el punto de venta",
                "justificacion": "Apriori detecta que estos productos se compran juntos mucho más de lo esperado por azar.",
                "impacto_estimado": "Mayor ticket promedio por venta cruzada",
                "riesgo": "bajo",
                "datos_citados": [f"Regla {r['antecedent']} -> {r['consequent']}: lift {r['lift']:.2f}, "
                                  f"confianza {r['confidence'] * 100:.0f}%, soporte {r['support'] * 100:.1f}%"]}

        # 3) Fidelización / reactivación
        segs = {s["segmento"]: s for s in c.get("segmentos", [])}
        reactivar = [segs[n] for n in ("En riesgo", "Perdidos") if n in segs]
        if reactivar:
            s = reactivar[0]
            acciones["clientes"] = {
                "accion": f"Campaña de reactivación para el segmento «{s['segmento']}» con un beneficio de hasta 10%",
                "justificacion": "Son clientes con alta recencia (hace tiempo no compran) que aún aportan valor.",
                "impacto_estimado": "Recuperar una fracción de los clientes inactivos",
                "riesgo": "medio", "descuento_pct": 10.0,
                "datos_citados": [f"Segmento {s['segmento']}: {s['n_clientes']} clientes, "
                                  f"recencia media {s['recencia_media']} días, ticket acumulado medio ${_fmt(s['monetario_medio'])}"]}
        elif "Campeones" in segs:
            s = segs["Campeones"]
            acciones["clientes"] = {
                "accion": "Programa de recompensas para el segmento «Campeones»",
                "justificacion": "Concentran la mayor frecuencia y valor monetario.",
                "impacto_estimado": "Retención de los clientes más rentables",
                "riesgo": "bajo",
                "datos_citados": [f"Campeones: {s['n_clientes']} clientes, valor medio ${_fmt(s['monetario_medio'])}"]}

        # 4) Calendario / estacionalidad
        fest = c.get("festivos_proximos_co", [])
        est = c.get("estacionalidad", {})
        if fest:
            f = fest[0]
            datos = [f"Festivo próximo: {f['nombre']} ({f['fecha']}), en {f['en_dias']} días"]
            if est.get("dia_pico"):
                datos.append(f"Día de la semana más fuerte: {est['dia_pico']}")
            if est.get("factor_mes_actual"):
                datos.append(f"Factor estacional del mes actual: {est['factor_mes_actual']}")
            acciones["calendario"] = {
                "accion": f"Preparar inventario y personal para {f['nombre']}",
                "justificacion": "Los festivos y los picos estacionales alteran la demanda frente al histórico reciente.",
                "impacto_estimado": "Atender la demanda del puente festivo sin quiebres",
                "riesgo": "medio", "datos_citados": datos}

        # 5) Margen
        cats = c.get("ventas_por_categoria_30d", [])
        if cats and k:
            acciones["margen"] = {
                "accion": f"Proteger el margen priorizando la categoría «{cats[0]['category']}»",
                "justificacion": "Es la categoría que más ingresos aporta; pequeños cambios de precio o costo mueven el resultado.",
                "impacto_estimado": "Sostener el margen global",
                "riesgo": "bajo",
                "datos_citados": [f"Margen 30d: {k.get('margen_pct', 0):.1f}% (${_fmt(k.get('margen', 0))})",
                                  f"{cats[0]['category']}: ${_fmt(cats[0]['ingresos'])} en 30 días"]}

        # Orden según palabras clave de la pregunta (determinístico)
        prioridad = []
        for clave, palabras in (("inventario", ("inventario", "stock", "repon", "demanda", "pedido")),
                                ("cruzada", ("cruz", "combo", "juntos", "ticket", "canasta")),
                                ("clientes", ("cliente", "fideli", "segment", "retener", "reactiv")),
                                ("calendario", ("festiv", "temporada", "estacion", "navidad", "calendario")),
                                ("margen", ("margen", "precio", "rentab", "ganancia", "descuento"))):
            if any(p in q for p in palabras):
                prioridad.append(clave)
        orden = prioridad + [x for x in ("inventario", "cruzada", "clientes", "calendario", "margen") if x not in prioridad]
        lista = [acciones[x] for x in orden if x in acciones][:5]
        resumen = (f"En los últimos 30 días se vendieron ${_fmt(k.get('total_ventas', 0))} en {k.get('n_ventas', 0)} ventas "
                   f"(ticket promedio ${_fmt(k.get('ticket_promedio', 0))}, margen {k.get('margen_pct', 0):.1f}%). "
                   f"Se proponen {len(lista)} acciones basadas en pronóstico de demanda, reglas de asociación y segmentación RFM.")
        return {"resumen": resumen, "acciones": lista, "advertencias": advertencias}
