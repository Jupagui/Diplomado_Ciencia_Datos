// Verificacion estatica de fondos animados, CSS, rutas y lanzador. Uso: node tests/check_static.mjs
import { readFileSync, existsSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const FRONT = join(dirname(fileURLToPath(import.meta.url)), '..');
const ROOT = join(FRONT, '..');
const rd = (p) => readFileSync(p, 'utf8');
let ok = 0, fail = 0;
const check = (nombre, cond, extra = '') => {
  if (cond) { ok++; console.log(`  ok   ${nombre}`); } else { fail++; console.log(`  FAIL ${nombre} ${extra}`); }
};

const shell = rd(join(FRONT, 'src/layout/AppShell.tsx'));
const app = rd(join(FRONT, 'src/App.tsx'));
const login = rd(join(FRONT, 'src/pages/Login.tsx'));
const fondoFn = shell.slice(shell.indexOf('function Fondo'), shell.indexOf('export function Marca'));

console.log('# Fondos por ruta (AppShell.Fondo)');
const comp = ['OrbitBackdrop', 'BlueprintBackdrop', 'Constellation', 'TopoRadar', 'SealTrace'];
for (const c of comp) {
  check(`${c}.tsx existe`, existsSync(join(FRONT, `src/ui/backgrounds/${c}.tsx`)));
  check(`${c} importado en AppShell`, new RegExp(`import \\{ ${c} \\} from '\\.\\./ui/backgrounds/${c}'`).test(shell));
}
check('useAnimatedSvg.ts existe', existsSync(join(FRONT, 'src/ui/backgrounds/useAnimatedSvg.ts')));
for (const c of comp) check(`${c} usa useAnimatedSvg`, rd(join(FRONT, `src/ui/backgrounds/${c}.tsx`)).includes('useAnimatedSvg'));

// ruta -> [fondo esperado], cada linea `if (ruta ...)` del Fondo
const lineas = fondoFn.split('\n').filter((l) => l.includes('if (ruta'));
const tabla = [
  ["ruta === '/'", 'OrbitBackdrop', ['aura a1', 'aura a2', 'scrim']],
  ["'/pos'", 'BlueprintBackdrop', ['scrim']],
  ["'/productos'", 'BlueprintBackdrop', ['scrim']],
  ["'/clientes'", 'BlueprintBackdrop', ['scrim']],
  ["'/analitica'", 'Constellation', ['scrim']],
  ["'/asesor'", 'TopoRadar', ['scrim']],
  ["'/datos'", 'SealTrace', ['scrim']],
];
for (const [clave, fondo, extras] of tabla) {
  const l = lineas.find((x) => x.includes(clave));
  check(`ruta ${clave.replace(/ruta === |'/g, '')} -> ${fondo}`, !!l && l.includes(`<${fondo} />`));
  for (const e of extras) check(`  ...con .${e}`, !!l && l.includes(`"${e}"`) || (!!l && l.includes(e)));
  check('  ...dentro de .backdrop', !!l && /className=(\{cls\('backdrop'|"backdrop")/.test(l));
}
check("Fondo se renderiza en el shell: <Fondo ruta={pathname} />", /<Fondo ruta=\{pathname\} \/>/.test(shell));
check('cada rama de Fondo tiene key distinta (cambio de fondo por ruta)',
  new Set([...fondoFn.matchAll(/key="([^"]+)"/g)].map((m) => m[1])).size === lineas.length);
check('Login: OrbitBackdrop a pantalla completa FUERA del shell',
  login.includes('<OrbitBackdrop />') && login.includes('className="backdrop is-home"') && !/AppShell\b.*Outlet/.test(login)
  && /<Route path="\/login" element=\{<Login \/>\} \/>/.test(app) && app.indexOf('/login') < app.indexOf('<AppShell'));

console.log('# Rutas de App.tsx: pagina + fondo');
const rutas = [...app.matchAll(/<Route path="(\/[^"]*)" element=\{<(\w+) \/>\}/g)].map((m) => [m[1], m[2]]);
const esperadas = { '/login': 'Login', '/': 'Inicio', '/pos': 'PuntoVenta', '/productos': 'Productos', '/clientes': 'Clientes',
  '/analitica': 'Analitica', '/asesor': 'Asesor', '/datos': 'Datos' };
for (const [r, p] of Object.entries(esperadas)) {
  check(`App.tsx ruta ${r} -> ${p}`, rutas.some(([rr, pp]) => rr === r && pp === p));
  check(`  pagina ${p}.tsx existe`, existsSync(join(FRONT, `src/pages/${p}.tsx`)));
  if (r !== '/login') {
    const l = r === '/' ? lineas.find((x) => x.includes("ruta === '/'")) : lineas.find((x) => x.includes(`'${r}'`));
    check(`  ruta ${r} tiene fondo en Fondo()`, !!l);
  }
}
check('NAV de AppShell enlaza todas las rutas del shell', ['/', '/pos', '/productos', '/clientes', '/analitica', '/asesor', '/datos'].every((r) => shell.includes(`to: '${r}'`)));

console.log('# CSS y keyframes');
const layout = rd(join(FRONT, 'src/styles/layout.css'));
const motion = rd(join(FRONT, 'src/styles/motion.css'));
const todoCss = ['tokens', 'base', 'motion', 'components', 'layout', 'app'].map((n) => rd(join(FRONT, `src/styles/${n}.css`))).join(' ');
for (const c of ['.backdrop', '.scrim', '.aura', '.photo', '.is-home']) check(`CSS define ${c}`, todoCss.includes(c));
const kf = [...motion.matchAll(/@keyframes\s+([\w-]+)/g)].map((m) => m[1]);
check(`motion.css tiene keyframes (${kf.length})`, kf.length >= 5, kf.join(','));
const baseCss = rd(join(FRONT, 'src/styles/base.css'));
check('main.tsx -> base.css importa tokens, motion, components, layout y app', ['tokens', 'motion', 'components', 'layout', 'app'].every((n) => baseCss.includes(`${n}.css`)));
const foto = layout.match(/\.photo[^}]*\}/s)?.[0] ?? '';
check('.photo no referencia bogota.jpg (imagen de Orbis)', !/bogota/i.test(foto + rd(join(FRONT, 'src/styles/app.css'))));

console.log('# Lanzador y docs');
const bat = rd(join(ROOT, 'iniciar_sistema.bat'));
check('bat: cd /d %~dp0', /cd \/d %~dp0/.test(bat));
check('bat: puerto 8010', /--port 8010/.test(bat));
check('bat: puerto 5180 (mensaje/URL)', bat.includes('5180'));
check('bat: no usa los puertos de Orbis 8000/5173', !/--port 8000|:5173|5173/.test(bat));
check('vite strictPort 5180', /port:\s*5180/.test(rd(join(FRONT, 'vite.config.ts'))) && /strictPort:\s*true/.test(rd(join(FRONT, 'vite.config.ts'))));
for (const f of ['README.md', 'CLAUDE.md']) {
  const t = existsSync(join(ROOT, f)) ? rd(join(ROOT, f)) : '';
  check(`${f} existe`, t.length > 200);
  check(`${f} menciona admin/admin123`, t.includes('admin') && t.includes('admin123'));
  check(`${f} menciona puertos 8010 y 5180`, t.includes('8010') && t.includes('5180'));
}
check('README explica como correr (iniciar_sistema.bat)', rd(join(ROOT, 'README.md')).includes('iniciar_sistema.bat'));

console.log(`\nResumen estatico: ${ok} ok, ${fail} fallan`);
process.exit(fail ? 1 : 0);
