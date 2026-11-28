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
frontend/      Vite + React 19 + TS · tema «Órbita» (copiado de Orbis) con la marca Red Rooster · fondos animados por ruta · Recharts
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

## Marca Red Rooster en el frontend
Sigue el *Manual de marca Red Rooster v1.0*: pizarra, gallo rojo y letra de cartel.

| Elemento | Dónde | Regla del manual |
|---|---|---|
| Colores | `src/styles/tokens.css` (`--rr-rojo`, `--rr-pizarra`, `--rr-tiza`, `--rr-mostaza`, `--rr-brasa`, `--rr-ocre`) | Tema oscuro = pizarra con texto tiza y acento mostaza; tema claro = tiza con texto pizarra y acento rojo |
| Fuentes | `public/fonts/` + `@font-face` en `src/styles/app.css`; Barlow por Google Fonts | Big Noodle: títulos, precios y números · Barlow: texto · Sunset Boulevard: nombre RED ROOSTER en el login (mín. 48 px) · Heartbreaking: lema |
| Logo | `public/marca/` | Gallo 3R rojo en la barra (espacio pequeño) · sello tiza en pizarra y sello rojo en tiza (login) · favicon = gallo 3R |
| Ilustración | `public/marca/bodegon-pollo.webp` en el fondo del Inicio | Nunca fotos de platos |
| Elementos | Tres estrellas en el antetítulo, línea con estrella en el lema, franja roja en la barra | Máximo dos recursos por pantalla además del logo |
| Gráficos | `--serie-1..6` leídas en `charts/paleta.ts` | Solo colores de la paleta |

Las versiones tiza y roja del sello y del gallo salen de los originales del sitio web (`WEBSITE/assets/images`) pintados en una sola tinta. **Licencias:** Heartbreaking y Sunset Boulevard son demos de Woodcutter; antes de publicar el sistema fuera del uso académico hay que comprar la licencia comercial o quitarlas (el respaldo es Big Noodle).

## Frontend: páginas
Inicio (KPIs, ventas, categorías, top y stock bajo) · Punto de venta · Productos (CRUD + kardex) · Clientes (PII enmascarada/revelable) · Analítica (demanda, venta cruzada, segmentos) · Asesor IA · Datos/ETL.
