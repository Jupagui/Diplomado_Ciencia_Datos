# CLAUDE.md — Sistema Micronegocios

## Antes de empezar
Lee siempre `PLAN.md` (fuente de verdad), `documento_srs_especificaci_n_t_cnica.md` y `BITACORA.md`. Al terminar cualquier tarea, actualiza `BITACORA.md` (fase, archivos clave, decisiones, estado).

## Puertos
- Backend FastAPI: **8010** (`/docs` para Swagger). Frontend Vite: **5180** (`strictPort`).
- Orbis usa 8000/5173: no chocar con él.

## Comandos
- Backend (desde `backend/`): `venv\Scripts\python -m uvicorn app.main:app --port 8010`; pruebas: `venv\Scripts\python -m pytest -q`.
- Frontend (desde `frontend/`): `npm run dev`, `npm run build` (tsc + vite), `npm run lint` (oxlint).
- Análisis de los objetivos 2 y 3 (desde `backend/`): `venv\Scripts\python -m analisis.correr_todo`; lee `red_rooster.db` en solo lectura y escribe en `backend/analisis/salidas/`.
- Todo junto: `iniciar_sistema.bat`.
- Credenciales demo: `admin` / `admin123` (configurables en `backend/.env`).

## Convenciones backend
- Python 3.13 en `backend/venv`. SQLite: la base activa es `backend/data/red_rooster.db` (datos reales; `micronegocio.db` es la sintética anterior).
- Hexagonal estricta: `domain/` no importa de `adapters/`; `application/` depende solo de los puertos (`domain/ports.py`); `etl/` y `ml/` trabajan sobre DataFrames y puertos, sin SQLAlchemy.
- Identificadores y comentarios en español. Fechas naive en hora local (UTC-5).
- Secretos nunca en el repo: solo `.env.example`; `.env`, `venv`, `data/*.db` están en `.gitignore`.
- Los fallos de pruebas se corrigen en el código de producción, no debilitando las pruebas.

## Convenciones frontend
- Diseño «Órbita» copiado de Orbis (`styles/`, `ui/`, `layout/AppShell.tsx`): no reescribir, extender. Estilos propios solo en `styles/app.css`, usando tokens.
- Marca Red Rooster (Manual de marca v1.0): los colores y fuentes están en `styles/tokens.css` (`--rr-*`, `--serie-1..6`, `--font-marca`, `--font-cartel`) y la capa de marca al final de `styles/app.css`. `--gold` = mostaza en pizarra y rojo en tiza. Nunca fotos de platos: solo ilustraciones (`public/marca/`). Rojo nunca como texto pequeño sobre pizarra; mostaza nunca sobre rojo. Precios y números en Big Noodle (`--font-display`): Heartbreaking y Sunset Boulevard son demo y no traen `$` ni tildes (Sunset tampoco números).
- Clave de tema: `mn-theme`. Token JWT: `mn-token` (localStorage); el interceptor de `services/api.ts` lo adjunta y ante 401 redirige a `/login`.
- Cada ruta monta su fondo animado en `AppShell.Fondo` (Inicio=OrbitBackdrop, POS/Productos/Clientes=Blueprint, Analítica=Constellation, Asesor=TopoRadar, Datos=SealTrace, Login=OrbitBackdrop).
- Gráficos con Recharts leyendo colores de los tokens con `usePaleta()` (`charts/paleta.ts`).
- Datos siempre con `useQuery`/`useMutation`; carga con `Skeleton`, vacíos con `EmptyState`.

## Datos del caso Red Rooster
- La fuente es `BD/pedidos.json` (datos reales) junto con `BD/productos.json`; `BD/` no se versiona.
- La clave HMAC `backend/data/.privacy_key` no se cambia (rompe los códigos de cliente `C###`).
- Costo faltante (`app/domain/costos.py`: `costo_es_real`, `costo_unitario`): un costo >= precio, 0 o nulo se trata como faltante y se estima con la mediana costo/precio de la categoría; el precio real es la mediana cobrada. Lo usan los KPIs de margen y valor de inventario, `etl/transform.imputar` y el paquete `analisis/`. No volver a tomar costo 0 como real.
- `backend/data/red_rooster.db` se reconstruye borrándola: el importador no borra pedidos ausentes del origen.
