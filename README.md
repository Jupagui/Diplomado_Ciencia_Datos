# MICRONEGOCIO — Sistema modular de gestión operativa y analítica predictiva

Plataforma para micronegocios (tienda de barrio / café) que captura transacciones en un esquema OLTP, las transforma con un ETL (Pandas) hacia un esquema analítico y entrega decisiones con tres modelos (XGBoost, Apriori, K-Means RFM) y un asesor generativo (Gemini, con modo simulado). Toda la visualización de BI es nativa en React (Recharts), sin herramientas de terceros. Especificación: `documento_srs_especificaci_n_t_cnica.md`; plan: `PLAN.md`; estado: `BITACORA.md`.

## Arquitectura (hexagonal)
```
backend/app
  core/        config, db (SQLAlchemy 2 síncrono), security (JWT + bcrypt)
  domain/      entities, ports (Protocol), errors, plan_accion (contrato Pydantic del asesor)
  application/ productos, clientes, ventas, inventario, kpis, analitica, asesor   (solo dependen de puertos)
  adapters/
    inbound/   api/v1 (auth, products, customers, sales, inventory, kpis, etl, analytics, advisor, health) + schemas
    outbound/  persistence (models, repositories), crypto (Fernet), llm (Gemini, simulado)
  etl/         extract (watermark, PII descifrada en memoria) · transform · load · pipeline
  ml/          demand_xgb · basket_apriori · rfm_kmeans
  seed/        generador_sintetico (semilla fija)
frontend/      Vite + React 19 + TS · tema «Órbita» (copiado de Orbis) · fondos animados por ruta · Recharts
```

## Modelo de datos
- **OLTP** (Anexo A del SRS, en snake_case): `products`, `customers` (email y teléfono cifrados con Fernet), `sales`, `sale_items`, `inventory_movements`.
- **Soporte**: `users` (login), `etl_runs` (watermark, estado, métricas JSON).
- **Analítico**: `analytics_demand_forecast`, `analytics_market_basket_rules`, `analytics_customer_segments`.
- **Desviaciones del SRS**: `products` suma `stock` y `unit_cost` (el SRS menciona stock y el KPI de margen necesita el costo); el margen usa el costo actual del producto. La baja de un producto es lógica (`is_active`). SQLite en lugar de un motor cliente-servidor. Las mermas del kardex pueden ser tipo `MERMA` o salidas con motivo.

## Cómo correrlo
Requisitos: Python 3.13, Node 22+.
- Todo: doble clic en `iniciar_sistema.bat` (crea el venv, instala dependencias y abre dos ventanas).
- A mano: `cd backend && python -m venv venv && venv\Scripts\pip install -r requirements.txt && venv\Scripts\uvicorn app.main:app --port 8010`, y `cd frontend && npm install && npm run dev`.
- Abrir http://localhost:5180 · API: http://localhost:8010/docs
- **Credenciales demo**: `admin` / `admin123` (variables `ADMIN_USER` / `ADMIN_PASSWORD` en `backend/.env`).
- La primera vez el backend siembra ~40 productos, ~300 clientes y 12 meses de ventas (≈ 20 s). Luego, en **Datos → Ejecutar pipeline** se entrenan los modelos.
- Gemini: define `GEMINI_API_KEY` (y opcionalmente `GEMINI_MODEL`) en `backend/.env`; sin clave el asesor responde en modo simulado (determinístico, desde las tablas analíticas).
- Pruebas: `cd backend && venv\Scripts\python -m pytest -q`.

## Métricas de los modelos (BD sembrada, semilla 42)
| Modelo | Métrica | Valor |
|---|---|---|
| XGBoost (demanda diaria, test = últimos 30 días) | MAE / R² | 1,27 u. / 0,32 (línea base lag-7: 1,59 / −0,16) |
| Apriori (soporte ≥ 0,02, confianza ≥ 0,3, lift > 1,2) | Reglas | 36 (lift máx. 21,7) |
| K-Means RFM (k por silueta, 2–6) | Silueta | 0,35 con k = 4 (Campeones, Leales, En riesgo, Perdidos) |

Los valores cambian ligeramente con la fecha de siembra (las ventas se generan relativas a «hoy»).

## Mapeo al SRS y a los roles
| SRS | Dónde está |
|---|---|
| Arquitectura hexagonal (2.1) | `domain/` · `application/` · `adapters/` |
| Modelo de datos y PII cifrada (2.2) | `adapters/outbound/persistence`, `crypto/fernet_cipher.py` |
| ETL: extracción, transformación, carga (2.3) | `app/etl/` (watermark en `etl_runs`) |
| XGBoost / Apriori / K-Means / Gemini (2.4) | `app/ml/`, `application/asesor.py`, `adapters/outbound/llm/` |
| BI nativo en HTML/React, KPIs (3) | `frontend/src/pages`, `frontend/src/charts` |
| Ingeniero de datos | ETL, esquema, cifrado, calidad (imputación de nulos) |
| Científico de datos | validación con MAE/R²/silueta/lift y split temporal sin fuga |
| Analista de decisiones e IA | asesor con guardrails (descuento ≤ 30 %, acciones con datos citados), contexto de festivos CO y estacionalidad |

## Frontend: páginas
Inicio (KPIs, ventas, categorías, top y stock bajo) · Punto de venta · Productos (CRUD + kardex) · Clientes (PII enmascarada/revelable) · Analítica (demanda, venta cruzada, segmentos) · Asesor IA · Datos/ETL.
