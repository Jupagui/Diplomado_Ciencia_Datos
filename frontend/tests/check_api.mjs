// Integracion frontend<->API real + E2E. Uso: API=http://127.0.0.1:8010/api/v1 node tests/check_api.mjs
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const FRONT = join(dirname(fileURLToPath(import.meta.url)), '..');
const API = process.env.API || 'http://127.0.0.1:8010/api/v1';
const ORIGEN = 'http://localhost:5180';
const src = readFileSync(join(FRONT, 'src/services/api.ts'), 'utf8');
let ok = 0, fail = 0;
const check = (n, c, extra = '') => { if (c) { ok++; console.log(`  ok   ${n}`); } else { fail++; console.log(`  FAIL ${n} ${extra}`); } };

async function http(metodo, ruta, { body, token, headers = {} } = {}) {
  const r = await fetch(API + ruta, { method: metodo, headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}), ...headers }, body: body ? JSON.stringify(body) : undefined });
  let j = null; try { j = await r.json(); } catch { /* sin cuerpo */ }
  return { status: r.status, json: j, headers: r.headers };
}

// ---- interfaces TS -> claves
function claves(nombre) {
  const ini = src.indexOf(`export interface ${nombre} {`);
  if (ini < 0) throw new Error('interfaz no encontrada: ' + nombre);
  // recorre llaves balanceadas
  let i = src.indexOf('{', ini), depth = 0, fin = i;
  for (; fin < src.length; fin++) { if (src[fin] === '{') depth++; else if (src[fin] === '}') { depth--; if (depth === 0) break; } }
  const cuerpo = src.slice(i + 1, fin);
  // solo nivel 1: quitar sub-objetos
  let plano = '', d = 0;
  for (const ch of cuerpo) { if (ch === '{') d++; else if (ch === '}') d--; else if (d === 0) plano += ch; }
  const res = [];
  for (const mm of plano.matchAll(/(?:^|[;\n])\s*(\w+)(\?)?\s*:/g)) res.push({ k: mm[1], opcional: !!mm[2] });
  return res;
}
function compara(nombre, obj, ctx) {
  const faltan = claves(nombre).filter((c) => !c.opcional && !(c.k in obj)).map((c) => c.k);
  check(`${ctx}: el JSON real trae todos los campos de ${nombre}`, faltan.length === 0, `faltan: ${faltan.join(',')}`);
}

// ---- 1) URLs usadas por el frontend vs OpenAPI
console.log('# URLs de api.ts vs /openapi.json');
const base = API.replace(/\/api\/v1$/, '');
const spec = await (await fetch(base + '/openapi.json')).json();
const rutasSpec = Object.entries(spec.paths).flatMap(([p, ops]) => Object.keys(ops).map((m) => [m.toUpperCase(), p]));
const llamadas = [...src.matchAll(/apiClient\.(get|post|put|delete)(?:<[\s\S]*?>)?\(\s*([`'])(\/[^`']*)\2/g)].map((m) => [m[1].toUpperCase(), m[3].replace(/\$\{[^}]*\}/g, '{x}')]);
check(`se detectaron llamadas en api.ts (${llamadas.length})`, llamadas.length >= 18);
const norm = (p) => p.replace(/\{[^}]*\}/g, '{x}');
for (const [m, p] of llamadas) check(`${m} ${p} existe en el backend`, rutasSpec.some(([mm, pp]) => mm === m && norm(pp.replace('/api/v1', '')) === norm(p)));
check('parser de interfaces funciona (Producto tiene 9 campos)', claves('Producto').length === 9, String(claves('Producto').length));

// ---- 2) E2E
console.log('# E2E por la API (flujo de la UI)');
const bad = await http('POST', '/auth/login', { body: { username: 'admin', password: 'x' } });
check('login incorrecto -> 401', bad.status === 401 && typeof bad.json?.detail === 'string');
const lg = await http('POST', '/auth/login', { body: { username: 'admin', password: 'admin123' } });
check('login ok', lg.status === 200 && lg.json.access_token && lg.json.username === 'admin');
const T = lg.json.access_token;
check('401 sin token en /products', (await http('GET', '/products')).status === 401);

const sku = 'E2E-' + Date.now();
const pc = await http('POST', '/products', { token: T, body: { sku, name: 'Producto E2E', category: 'Pruebas', unit_price: 5000, unit_cost: 2000, stock: 10 } });
check('crear producto 201', pc.status === 201); compara('Producto', pc.json, 'POST /products');
const pid = pc.json.id;
const lst = await http('GET', '/products?limit=1000&solo_activos=true', { token: T });
check('listar productos incluye el nuevo', lst.json.some((p) => p.id === pid)); compara('Producto', lst.json[0], 'GET /products');
const cats = await http('GET', '/products/categories', { token: T });
check('categorias es string[]', Array.isArray(cats.json) && cats.json.every((c) => typeof c === 'string') && cats.json.includes('Pruebas'));
const up = await http('PUT', `/products/${pid}`, { token: T, body: { name: 'Producto E2E 2', unit_price: 5500 } });
check('PUT producto', up.status === 200 && up.json.unit_price === 5500);

const cl = await http('GET', '/customers?limit=500', { token: T });
check('clientes enmascarados por defecto', cl.status === 200 && cl.json[0].revelado === false && cl.json[0].email.includes('***')); compara('Cliente', cl.json[0], 'GET /customers');
const clr = await http('GET', '/customers?limit=500&revelar=true', { token: T });
check('revelar=true muestra PII', clr.json[0].revelado === true && clr.json[0].email.includes('@') && !clr.json[0].email.includes('***'));
const cid = cl.json[0].id;

const ven = await http('POST', '/sales', { token: T, body: { items: [{ product_id: pid, quantity: 3 }], payment_method: 'EFECTIVO', customer_id: cid } });
check('venta 201', ven.status === 201 && ven.json.total_amount === 16500); compara('Venta', ven.json, 'POST /sales'); compara('ItemVenta', ven.json.items[0], 'POST /sales items');
const pAfter = await http('GET', `/products/${pid}`, { token: T });
check('stock descontado (10 -> 7)', pAfter.json.stock === 7);
const mv = await http('GET', `/inventory/movements?product_id=${pid}&limit=100`, { token: T });
check('kardex: IN inicial + OUT de la venta', mv.json.length === 2 && mv.json.some((m) => m.movement_type === 'OUT' && m.quantity === 3) && mv.json.some((m) => m.movement_type === 'IN'));
compara('Movimiento', mv.json[0], 'GET /inventory/movements');
const rechazo = await http('POST', '/sales', { token: T, body: { items: [{ product_id: pid, quantity: 99 }], payment_method: 'EFECTIVO' } });
check('venta sin stock -> 409 con detail (lo muestra el POS)', rechazo.status === 409 && typeof rechazo.json.detail === 'string');
const mm = await http('POST', '/inventory/movements', { token: T, body: { product_id: pid, movement_type: 'MERMA', quantity: 1, reason: 'prueba' } });
check('registrar movimiento MERMA', mm.status === 201);
const low = await http('GET', '/inventory/low-stock?umbral=15', { token: T });
check('low-stock devuelve productos', low.status === 200 && Array.isArray(low.json)); if (low.json.length) compara('Producto', low.json[0], 'GET /inventory/low-stock');

const k = await http('GET', '/kpis/resumen?dias=30&top=8', { token: T });
check('kpis 200', k.status === 200); compara('Kpis', k.json, 'GET /kpis/resumen');
check('kpis: top_productos[].campos', k.json.top_productos.length > 0 && ['product_id', 'name', 'category', 'unidades', 'ingresos'].every((c) => c in k.json.top_productos[0]));
check('kpis: ventas_por_categoria[].campos', k.json.ventas_por_categoria.length > 0 && ['category', 'unidades', 'ingresos'].every((c) => c in k.json.ventas_por_categoria[0]));
check('kpis: serie_diaria[].campos', k.json.serie_diaria.length > 0 && ['fecha', 'total', 'n_ventas'].every((c) => c in k.json.serie_diaria[0]));

const sinEtl = await http('GET', '/analytics/metrics', { token: T });
check('metrics antes del ETL: disponible=false, campos presentes', sinEtl.json.disponible === false); compara('Metricas', sinEtl.json, 'GET /analytics/metrics (sin ETL)');
const etl = await http('POST', '/etl/run?force=true', { token: T });
check('ETL force -> SUCCESS', etl.status === 200 && etl.json.status === 'SUCCESS', JSON.stringify(etl.json).slice(0, 200)); compara('EtlRun', etl.json, 'POST /etl/run');
const runs = await http('GET', '/etl/runs?limit=20', { token: T });
check('runs: lista con el ultimo run', runs.json[0].id === etl.json.id); compara('EtlRun', runs.json[0], 'GET /etl/runs');

for (const h of [7, 30]) {
  const d = await http('GET', `/analytics/demand?horizon=${h}`, { token: T });
  check(`demanda ${h}d`, d.status === 200 && d.json.length > 0 && d.json[0].diaria.length === h);
  compara('DemandaProducto', d.json[0], `GET /analytics/demand ${h}`);
  check('  diaria[].{fecha,cantidad}', 'fecha' in d.json[0].diaria[0] && 'cantidad' in d.json[0].diaria[0]);
}
const reg = await http('GET', '/analytics/basket?limit=100', { token: T });
check('reglas', reg.status === 200 && reg.json.length > 0 && reg.json.every((r) => r.lift > 1.2)); compara('Regla', reg.json[0], 'GET /analytics/basket');
const seg = await http('GET', '/analytics/segments', { token: T });
check('segmentos', seg.status === 200 && seg.json.resumen.length > 0 && seg.json.clientes.length > 0);
compara('Segmentos', seg.json, 'GET /analytics/segments'); compara('ResumenSegmento', seg.json.resumen[0], 'segments.resumen'); compara('ClienteSegmento', seg.json.clientes[0], 'segments.clientes');
const met = await http('GET', '/analytics/metrics', { token: T });
check('metricas disponibles', met.json.disponible === true && met.json.mae >= 0 && Number.isFinite(met.json.r2) && met.json.silhouette >= -1 && met.json.silhouette <= 1 && met.json.n_reglas > 0);
compara('Metricas', met.json, 'GET /analytics/metrics');

console.log('# Campos anidados leidos por las paginas (metrics.detalle / runs[].metrics)');
const dt = met.json.detalle;
const rutas = [['demanda', 'mae_baseline_lag7'], ['demanda', 'n_test'], ['demanda', 'dias_historia'], ['demanda', 'model_version'],
  ['canasta', 'min_support'], ['canasta', 'min_confidence'], ['canasta', 'min_lift'], ['canasta', 'n_canastas'], ['canasta', 'lift_max'],
  ['segmentos', 'n_clientes']];
for (const [a, b] of rutas) check(`detalle.${a}.${b} existe (${JSON.stringify(dt?.[a]?.[b])})`, !!dt?.[a] && b in dt[a] && dt[a][b] !== null);
check('runs[0].metrics.demanda.model_version (columna de Datos.tsx)', !!runs.json[0].metrics?.demanda?.model_version);
check('runs[].duracion_s numerico (columna de Datos.tsx)', typeof runs.json[0].duracion_s === 'number');
const noop = await http('POST', '/etl/run?force=false', { token: T });
check('ETL sin force y sin ventas nuevas -> SIN_CAMBIOS (lo que muestra Datos.tsx)', noop.json.status === 'SIN_CAMBIOS');
check('run SIN_CAMBIOS: metrics.mensaje (Datos.tsx)', typeof noop.json.metrics?.mensaje === 'string');
check('seg.resumen etiquetas validas', seg.json.resumen.every((r) => ['Campeones', 'Leales', 'En riesgo', 'Perdidos', 'Nuevos', 'Ocasionales'].includes(r.segmento)));

const ad = await http('POST', '/advisor/ask', { token: T, body: { pregunta: '¿Qué debo reponer esta semana?' } });
check('asesor 200 modo simulado', ad.status === 200 && ad.json.modo === 'simulado'); compara('PlanAccion', ad.json, 'POST /advisor/ask');
check('asesor: acciones con los campos de AccionPlan', ad.json.acciones.length >= 1 && ad.json.acciones.length <= 5 && ad.json.acciones.every((a) => claves('AccionPlan').every((c) => c.k in a)));
check('asesor: datos_citados no vacios', ad.json.acciones.every((a) => a.datos_citados.length > 0));
check('asesor pregunta vacia -> 422', (await http('POST', '/advisor/ask', { token: T, body: { pregunta: '' } })).status === 422);

const des = await fetch(`${API}/products/${pid}`, { method: 'DELETE', headers: { Authorization: `Bearer ${T}` } });
check('DELETE producto 204 (baja logica)', des.status === 204);

// ---- 3) CORS
console.log('# CORS desde ' + ORIGEN);
const pre = await fetch(`${API}/sales`, { method: 'OPTIONS', headers: { Origin: ORIGEN, 'Access-Control-Request-Method': 'POST', 'Access-Control-Request-Headers': 'authorization,content-type' } });
check('preflight 200', pre.status === 200);
check('allow-origin = origen del frontend', pre.headers.get('access-control-allow-origin') === ORIGEN, String(pre.headers.get('access-control-allow-origin')));
check('allow-headers incluye authorization', /authorization/i.test(pre.headers.get('access-control-allow-headers') || ''));
const real = await http('GET', '/products?limit=1', { token: T, headers: { Origin: ORIGEN } });
check('GET con Origin recibe allow-origin', real.headers.get('access-control-allow-origin') === ORIGEN);
const ajeno = await fetch(`${API}/health`, { headers: { Origin: 'http://evil.example' } });
check('origen ajeno NO recibe allow-origin', !ajeno.headers.get('access-control-allow-origin'));
const e401 = await http('GET', '/products', { headers: { Origin: ORIGEN } });
check('401 tambien lleva CORS (para que el interceptor lo vea)', e401.status === 401 && e401.headers.get('access-control-allow-origin') === ORIGEN);

console.log(`\nResumen API/E2E: ${ok} ok, ${fail} fallan`);
process.exit(fail ? 1 : 0);
