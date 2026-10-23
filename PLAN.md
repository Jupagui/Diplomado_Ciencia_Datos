# Plan: Sistema Modular de Gestión Operativa y Analítica Predictiva (Diplomado Ciencia de Datos)

## Context
El SRS (`E:\Desarrollos\Diplomado Ciencia de datos\documento_srs_especificaci_n_t_cnica.md`) define una plataforma para micronegocios con:
- FastAPI con arquitectura hexagonal, más React.
- Base OLTP con PII cifrada con Fernet.
- ETL con Pandas.
- 3 modelos: XGBoost para demanda, Apriori para venta cruzada y K-Means RFM.
- Asesor Gemini con contratos Pydantic.
- BI nativo en React, sin Power BI.

La carpeta solo contiene el `.md`, así que el proyecto se construye desde cero, con **el mismo diseño visual de Orbis** (`E:\Ia_integrada\Orbis`). La construcción la hacen **2 agentes Sonnet**: un ejecutor y un tester.

**Decisiones del usuario:**
- Base de datos SQLite.
- Generador de datos sintéticos.
- Gemini con `GEMINI_API_KEY` y modo simulado si no hay key.
- Login JWT simple con un usuario admin.

**Entorno:** Python 3.13.7, Node 22.19, npm 10.9.

## Qué se reutiliza de Orbis
Orbis es Vite + React 19 + TS + react-router 7 + TanStack Query + axios, con CSS propio basado en variables. No usa Tailwind ni librería de componentes. El tema "Órbita" es oscuro primero, con dorado y salvia, y tipografías Bodoni Moda, Jost e IBM Plex Mono. Se **copia sin cambios** y luego se adapta la marca:
- `frontend/src/styles/`: `tokens.css`, `base.css`, `motion.css`, `components.css` y `layout.css`.
- `frontend/src/ui/`: `theme.ts`, `cls.ts`, `format.ts`, `contrast.ts`, `Surfaces.tsx` (Card, Stat como KPI, Alert, EmptyState, Skeleton, Progress), `Button.tsx`, `Badges.tsx`, `Inputs.tsx` (Field, Segmented, Tabs, ThemeSwitch), `Overlays.tsx` (Sheet), `Toast.tsx`, `useToast.ts`, `Icon.tsx`, `iconNames.ts`, `Chat.tsx`, `backgrounds/`.
- `frontend/index.html`: Google Fonts y el script de tema antes del primer pintado. La clave de localStorage cambia a `mn-theme`.
- `frontend/src/layout/AppShell.tsx`: topbar de vidrio, bottom-nav en móvil, `<Marca/>` con la órbita y fondos animados. Se cambia el texto de marca y el `NAV`.
- Patrón de páginas: `.page`, luego `.page-head` con `.eyebrow` y `h1.title` (con `<em>` dorado), luego las grillas de `.card`. Las tablas usan `.tbl-wrap > table.tbl`.
- `iniciar_sistema.bat` como plantilla del lanzador.
- Configuración backend en el estilo de Orbis: `core/config.py` con pydantic-settings y `get_settings()` en caché, y lifespan con `create_all` más seed en `main.py`.
- La idea de `providers/ai.py` (fachada Gemini) se reutiliza como adaptador LLM.

### Fondos animados (obligatorio)
- **Archivos que se copian:** todo `frontend/src/ui/backgrounds/` (`OrbitBackdrop`, `BlueprintBackdrop`, `Constellation`, `SealTrace`, `TopoRadar` y `useAnimatedSvg.ts`), junto con las reglas `.backdrop`, `.scrim`, `.aura`, `.photo` e `.is-home` de `layout.css` y los keyframes de `motion.css`.
- **Componente:** `AppShell.tsx` conserva su componente `Fondo({ruta})`, que cambia de fondo según la ruta con su `key`, como en Orbis.
- **Asignación por página:**

  | Página | Fondo |
  |---|---|
  | Inicio | `OrbitBackdrop` con `.aura.a1` y `.aura.a2`. La capa `.photo` se quita o se reemplaza por una imagen neutra, porque la de Orbis es bogota.jpg |
  | Punto de venta y Productos | `BlueprintBackdrop` |
  | Analítica | `Constellation` |
  | Asesor IA | `TopoRadar` |
  | Datos/ETL | `SealTrace` |
  | Login | `OrbitBackdrop` a pantalla completa, sin shell |

- **Comportamiento:** se mantienen la pausa fuera de pantalla y el respeto a `prefers-reduced-motion` que ya da `useAnimatedSvg.ts`, y la entrada escalonada `.rise` con `--i` en las tarjetas.
- **Verificación:** el tester confirma que cada página monta su fondo. Yo lo reviso visualmente al final.

**Lo que Orbis no tiene y se agrega:**
- **Gráficos:** Recharts, con colores leídos de los tokens mediante `leerVar()` de `theme.ts`.
- **Login JWT.**
- **Arquitectura hexagonal** real.
- **Puertos 8010 y 5180**, para no chocar con Orbis (8000 y 5173).

## Estructura objetivo (`E:\Desarrollos\Diplomado Ciencia de datos\`)
```
backend/
  requirements.txt  .env.example  pytest.ini
  app/
    main.py                         lifespan: create_all + seed admin + datos sintéticos si la BD está vacía
    core/ config.py db.py security.py (JWT con PyJWT, bcrypt)
    domain/ entities.py (dataclasses)  ports.py (Protocol: ProductRepo, CustomerRepo, SaleRepo,
            InventoryRepo, AnalyticsRepo, CipherPort, AdvisorPort)  errors.py
    application/ productos.py clientes.py ventas.py (registra la venta, descuenta stock y crea el movimiento OUT)
                 inventario.py kpis.py analitica.py asesor.py   ← dependen solo de los puertos
    adapters/
      inbound/api/v1/ auth products customers sales inventory kpis etl analytics advisor health
      inbound/schemas/              DTOs Pydantic
      outbound/persistence/ models.py (SQLAlchemy 2.0 síncrono) repositories.py
      outbound/crypto/fernet_cipher.py
      outbound/llm/ gemini_advisor.py  mock_advisor.py
    etl/ extract.py (incremental por watermark, descifra la PII en memoria) transform.py (nulos, lags,
         ventanas móviles, matriz binaria de canasta, tabla RFM, festivos CO) load.py pipeline.py
    ml/ demand_xgb.py (horizonte 7/30 d, MAE y R² con split temporal) basket_apriori.py (mlxtend, lift>1.2)
        rfm_kmeans.py (k elegido por silueta, k=2..6)
    seed/ generador_sintetico.py    ~40 productos, ~300 clientes, 12 meses de ventas con estacionalidad,
                                    fin de semana, festivos (`holidays` CO) y combos frecuentes
  tests/ unit/ (dominio, casos de uso con repos falsos, cifrado, ETL, modelos) api/ (TestClient + SQLite temporal)
frontend/                           Vite + React 19 + TS (mismas versiones que Orbis) + recharts
  src/services/api.ts               axios con baseURL desde VITE_API_URL e interceptor Bearer y 401 → /login
  src/auth/ AuthContext.tsx RequireAuth.tsx
  src/pages/ Login Inicio(dashboard KPIs) PuntoVenta Productos(+kardex) Clientes Analitica(tabs: Demanda,
             Venta cruzada, Segmentos) Asesor(chat IA) Datos(ETL: ejecutar, estado, métricas de modelos)
  src/charts/ LineaDemanda BarrasCategoria DonaSegmentos DispersionRFM  (Recharts con los tokens)
iniciar_sistema.bat  README.md  CLAUDE.md  BITACORA.md
.claude/agents/ ejecutor-plan.md  tester-qa.md
```

## Modelo de datos
- **Tablas OLTP:** se usan las del Anexo A tal cual, con nombres en snake_case en SQLAlchemy.
- **Columnas agregadas a Products:** `stock INTEGER` y `unit_cost DECIMAL`. El texto del SRS menciona stock, y el KPI de margen necesita el costo. Esta desviación queda documentada en el README.
- **Tablas extra:**
  - `users`, para el login.
  - `etl_runs`, con el watermark, el estado y las métricas en JSON.
  - `analytics_demand_forecast`, con `product_id`, `forecast_date`, `horizon`, `predicted_qty`, `model_version`.
  - `analytics_market_basket_rules`, con antecedente, consecuente, support, confidence y lift.
  - `analytics_customer_segments`, con `customer_id`, R, F, M, `cluster` y `segment_label`.
- **Cifrado:** `encrypted_email` y `encrypted_phone` se cifran con Fernet. La clave va en `.env` (`FERNET_KEY`) y se genera si falta, en modo dev. La API devuelve la PII enmascarada por defecto.

## API (prefijo `/api/v1`, todo protegido con JWT salvo `/auth/login` y `/health`)
- `POST /auth/login`
- CRUD de `/products` y `/customers`
- `POST /sales`, que es transaccional: valida el stock antes de registrar. También `GET /sales`.
- `GET|POST /inventory/movements`, que funciona como kardex.
- `GET /kpis/resumen`: ventas, ticket promedio, margen, rotación, top productos y serie diaria.
- `POST /etl/run`, que ejecuta el ETL y entrena los 3 modelos. También `GET /etl/runs`.
- `GET /analytics/demand?horizon=7|30`, `/analytics/basket`, `/analytics/segments` y `/analytics/metrics`.
- `POST /advisor/ask`: devuelve un `PlanAccion` validado por Pydantic con resumen, acciones (acción, justificación, impacto, riesgo) y advertencias.
  - **Guardrails (red teaming):** se rechazan los descuentos mayores al 30% y las acciones que no citen datos analíticos. Hay un reintento si el JSON no es válido.
  - **Modo simulado:** si no hay key, `MockAdvisor` arma el plan de forma determinística desde las tablas analíticas.

## Los 2 agentes (ambos con `model: sonnet`)
Ambos se crean como archivos reutilizables en `E:\Desarrollos\Diplomado Ciencia de datos\.claude\agents\` y se lanzan con el tool Agent pasando `model: "sonnet"`.

1. **`ejecutor-plan`:** implementa este plan por fases. Recibe la ruta de Orbis para copiar los estilos y componentes, y anota cada fase en `BITACORA.md`.
2. **`tester-qa`:** escribe y corre las pruebas e informa los fallos con su salida. No arregla código de producción, solo las pruebas.

**Regla de cierre: ningún agente queda a medias.**
- Espero la notificación de cada agente antes de lanzar el siguiente paso. Nunca doy una fase por terminada sin su reporte.
- Si un agente se detiene sin terminar, por límite o por un error, lo retomo con SendMessage, sin abrir uno nuevo, hasta que reporte la fase completa.
- El ciclo de cada fase es: ejecutor → tester → (hay fallos → ejecutor corrige → tester repite). Se repite hasta que el tester reporte **0 fallos**.
- No cierro la sesión hasta que el tester de la Fase 3 reporte todo en verde. Al final hago una revisión mía: pytest, build y la página abierta.
- `BITACORA.md` registra el estado de cada fase (pendiente, en curso, en verde), para saber exactamente dónde quedó todo si algo se corta.

**Flujo** (yo coordino; si el tester encuentra fallos, se los devuelvo al ejecutor con SendMessage hasta que todo quede en verde):
- **Fase 1 (ejecutor):** backend con dominio, puertos, persistencia, cifrado, auth, generador sintético, CRUD, ventas y KPIs.
- **Fase 1 (tester):** pytest unitario y de API, más arrancar uvicorn y hacer curls de humo.
- **Fase 2 (ejecutor):** ETL, ML, tablas analíticas, asesor Gemini o simulado, y sus endpoints.
- **Fase 2 (tester):** pruebas de ETL y modelos (métricas presentes y válidas: R² finito, silueta entre -1 y 1, lift > 1.2) y del contrato del asesor y sus guardrails.
- **Fase 3 (ejecutor):** frontend con el diseño de Orbis, todas las páginas, el lanzador `.bat`, el README y el CLAUDE.md.
- **Fase 3 (tester):** `npm run build`, `npm run lint` y un recorrido E2E por la API con los mismos flujos que usa la UI (login → venta → ETL → analítica → asesor).

## Verificación
- `cd backend && venv\Scripts\python -m pytest -q`: todo en verde.
- `uvicorn app.main:app --port 8010`:
  - `GET /api/v1/health` responde 200.
  - Login → `POST /etl/run` → `/analytics/metrics` devuelve MAE, R², silueta y el número de reglas.
- `cd frontend && npm run build` sin errores de TypeScript, más `npm run lint`.
- Al final abro `http://localhost:5180` y reviso:
  - Login y dashboard con el tema Órbita, en oscuro y en claro.
  - Que los gráficos se vean en ambos temas.
  - El POS registrando una venta.
  - El asesor respondiendo en modo simulado.
