# CLAUDE.md — Sistema Micronegocios

## Antes de empezar
Lee siempre `PLAN.md` (fuente de verdad), `documento_srs_especificaci_n_t_cnica.md` y `BITACORA.md`. Al terminar cualquier tarea, actualiza `BITACORA.md` (fase, archivos clave, decisiones, estado).

## Puertos
- Backend FastAPI: **8010** (`/docs` para Swagger). Frontend Vite: **5180** (`strictPort`).
- Orbis usa 8000/5173: no chocar con él.

## Comandos
- Backend (desde `backend/`): `venv\Scripts\python -m uvicorn app.main:app --port 8010`; pruebas: `venv\Scripts\python -m pytest -q`.
- Frontend (desde `frontend/`): `npm run dev`, `npm run build` (tsc + vite), `npm run lint` (oxlint).
- Todo junto: `iniciar_sistema.bat`.
- Credenciales demo: `admin` / `admin123` (configurables en `backend/.env`).

## Convenciones backend
- Python 3.13 en `backend/venv`. SQLite en `backend/data/micronegocio.db` (se siembra sola si está vacía).
- Hexagonal estricta: `domain/` no importa de `adapters/`; `application/` depende solo de los puertos (`domain/ports.py`); `etl/` y `ml/` trabajan sobre DataFrames y puertos, sin SQLAlchemy.
- Identificadores y comentarios en español. Fechas naive en hora local (UTC-5).
- Secretos nunca en el repo: solo `.env.example`; `.env`, `venv`, `data/*.db` están en `.gitignore`.
- Los fallos de pruebas se corrigen en el código de producción, no debilitando las pruebas.

## Convenciones frontend
- Diseño «Órbita» copiado de Orbis (`styles/`, `ui/`, `layout/AppShell.tsx`): no reescribir, extender. Estilos propios solo en `styles/app.css`, usando tokens.
- Clave de tema: `mn-theme`. Token JWT: `mn-token` (localStorage); el interceptor de `services/api.ts` lo adjunta y ante 401 redirige a `/login`.
- Cada ruta monta su fondo animado en `AppShell.Fondo` (Inicio=OrbitBackdrop, POS/Productos/Clientes=Blueprint, Analítica=Constellation, Asesor=TopoRadar, Datos=SealTrace, Login=OrbitBackdrop).
- Gráficos con Recharts leyendo colores de los tokens con `usePaleta()` (`charts/paleta.ts`).
- Datos siempre con `useQuery`/`useMutation`; carga con `Skeleton`, vacíos con `EmptyState`.
