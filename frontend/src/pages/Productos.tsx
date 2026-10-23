import { useState, type FormEvent } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  actualizarProducto, crearProducto, desactivarProducto, getCategorias, getMovimientos, getProductos, mensajeError,
  registrarMovimiento, type Producto,
} from '../services/api';
import { Pill, StatusPill } from '../ui/Badges';
import { Button } from '../ui/Button';
import { Field, Select, Switch } from '../ui/Inputs';
import { Sheet } from '../ui/Overlays';
import { Alert, Card, CardHeader, EmptyState, Skeleton } from '../ui/Surfaces';
import { vars } from '../ui/cls';
import { formatoCOP, formatoFecha, formatoNum } from '../ui/format';
import { useToast } from '../ui/useToast';

interface Borrador { sku: string; name: string; category: string; unit_price: string; unit_cost: string; stock: string; is_active: boolean }
const VACIO: Borrador = { sku: '', name: '', category: '', unit_price: '', unit_cost: '', stock: '0', is_active: true };

function Kardex({ producto }: { producto: Producto }) {
  const qc = useQueryClient();
  const avisar = useToast();
  const [tipo, setTipo] = useState('IN');
  const [cant, setCant] = useState('');
  const [motivo, setMotivo] = useState('');
  const [error, setError] = useState('');
  const movs = useQuery({ queryKey: ['kardex', producto.id], queryFn: () => getMovimientos(producto.id) });

  const registrar = useMutation({
    mutationFn: () => registrarMovimiento({ product_id: producto.id, movement_type: tipo, quantity: Number(cant), reason: motivo || undefined }),
    onSuccess: () => {
      avisar('Movimiento registrado', 'ok');
      setCant(''); setMotivo(''); setError('');
      void qc.invalidateQueries({ queryKey: ['kardex', producto.id] });
      void qc.invalidateQueries({ queryKey: ['productos'] });
      void qc.invalidateQueries({ queryKey: ['stock-bajo'] });
    },
    onError: (e) => setError(mensajeError(e)),
  });

  return (
    <div className="stack">
      <form className="stack" onSubmit={(e) => { e.preventDefault(); if (Number(cant) > 0) registrar.mutate(); }}>
        <div className="grid-2">
          <Select label="Tipo de movimiento" value={tipo} onChange={(e) => setTipo(e.target.value)}>
            <option value="IN">Entrada (compra / reposición)</option>
            <option value="OUT">Salida (ajuste)</option>
            <option value="MERMA">Merma</option>
          </Select>
          <Field label="Cantidad" type="number" min={1} step={1} value={cant} onChange={(e) => setCant(e.target.value)} required />
        </div>
        <Field label="Motivo (opcional)" value={motivo} onChange={(e) => setMotivo(e.target.value)} maxLength={255} />
        {error && <Alert tone="danger" title="No se pudo registrar" role="alert">{error}</Alert>}
        <Button type="submit" icon="mas" loading={registrar.isPending} disabled={!(Number(cant) > 0)}>Registrar movimiento</Button>
      </form>
      <h3 style={{ fontSize: 'var(--fs-4)' }}>Kardex</h3>
      {movs.isLoading ? <Skeleton ancho="100%" /> : !movs.data?.length ? <EmptyState icon="historial" title="Sin movimientos" /> : (
        <div className="tbl-wrap">
          <table className="tbl">
            <thead><tr><th>Fecha</th><th>Tipo</th><th className="num-cell">Cant.</th><th>Motivo</th></tr></thead>
            <tbody>
              {movs.data.map((m) => (
                <tr key={m.id}>
                  <td>{formatoFecha(m.created_at, true)}</td>
                  <td><span className={m.movement_type === 'IN' ? 'mov-in' : 'mov-out'}>{m.movement_type === 'IN' ? 'Entrada' : m.movement_type === 'OUT' ? 'Salida' : 'Merma'}</span></td>
                  <td className="num-cell">{m.movement_type === 'IN' ? '+' : '−'}{m.quantity}</td>
                  <td className="muted">{m.reason ?? '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

export default function Productos() {
  const qc = useQueryClient();
  const avisar = useToast();
  const [q, setQ] = useState('');
  const [verInactivos, setVerInactivos] = useState(false);
  const [editando, setEditando] = useState<Producto | 'nuevo' | null>(null);
  const [kardex, setKardex] = useState<Producto | null>(null);
  const [b, setB] = useState<Borrador>(VACIO);
  const [error, setError] = useState('');

  const productos = useQuery({ queryKey: ['productos', 'todos', q], queryFn: () => getProductos({ q: q || undefined }) });
  const categorias = useQuery({ queryKey: ['categorias'], queryFn: getCategorias });
  const lista = (productos.data ?? []).filter((p) => verInactivos || p.is_active);

  const abrir = (p: Producto | 'nuevo') => {
    setError('');
    setB(p === 'nuevo' ? VACIO : { sku: p.sku, name: p.name, category: p.category ?? '', unit_price: String(p.unit_price), unit_cost: String(p.unit_cost), stock: String(p.stock), is_active: p.is_active });
    setEditando(p);
  };
  const refrescar = () => {
    void qc.invalidateQueries({ queryKey: ['productos'] });
    void qc.invalidateQueries({ queryKey: ['categorias'] });
    void qc.invalidateQueries({ queryKey: ['stock-bajo'] });
  };

  const guardar = useMutation({
    mutationFn: async () => {
      const base = { name: b.name.trim(), category: b.category.trim() || null, unit_price: Number(b.unit_price), unit_cost: Number(b.unit_cost || 0) };
      if (editando === 'nuevo') return crearProducto({ ...base, sku: b.sku.trim(), stock: Number(b.stock || 0) });
      return actualizarProducto((editando as Producto).id, { ...base, is_active: b.is_active });
    },
    onSuccess: () => { avisar(editando === 'nuevo' ? 'Producto creado' : 'Producto actualizado', 'ok'); setEditando(null); refrescar(); },
    onError: (e) => setError(mensajeError(e)),
  });
  const baja = useMutation({
    mutationFn: (id: number) => desactivarProducto(id),
    onSuccess: () => { avisar('Producto desactivado', 'ok'); setEditando(null); refrescar(); },
    onError: (e) => setError(mensajeError(e)),
  });

  const enviar = (e: FormEvent) => { e.preventDefault(); setError(''); guardar.mutate(); };
  const campo = (k: keyof Borrador) => ({ value: b[k] as string, onChange: (e: { target: { value: string } }) => setB({ ...b, [k]: e.target.value }) });
  const nuevo = editando === 'nuevo';

  return (
    <div className="page">
      <header className="page-head">
        <p className="eyebrow rise" style={vars({ '--i': 0 })}>Catálogo e inventario</p>
        <h1 className="title rise" style={vars({ '--i': 1 })}>Tus <em>productos</em></h1>
      </header>

      <Card className="rise" style={vars({ '--i': 2 })}>
        <CardHeader icon="caja" title="Catálogo" aside={<Button icon="mas" onClick={() => abrir('nuevo')}>Nuevo producto</Button>} />
        <div className="toolbar" style={{ marginBottom: 'var(--sp-2)' }}>
          <Field label="Buscar" hideLabel icon="buscar" placeholder="Buscar por nombre o SKU…" value={q} onChange={(e) => setQ(e.target.value)} />
          <label className="row-gap small muted"><Switch checked={verInactivos} onChange={setVerInactivos} label="Mostrar inactivos" /> Mostrar inactivos</label>
        </div>
        {productos.isError && <Alert tone="danger" title="No se pudo cargar el catálogo" role="alert">{mensajeError(productos.error)}</Alert>}
        {productos.isLoading ? <Skeleton ancho="100%" /> : !lista.length ? <EmptyState icon="caja" title="Sin productos" action={<Button icon="mas" onClick={() => abrir('nuevo')}>Crear el primero</Button>} /> : (
          <div className="tbl-wrap">
            <table className="tbl">
              <thead><tr><th>SKU</th><th>Producto</th><th>Categoría</th><th className="num-cell">Precio</th><th className="num-cell">Costo</th><th className="num-cell">Stock</th><th>Estado</th><th><span className="sr-only">Acciones</span></th></tr></thead>
              <tbody>
                {lista.map((p) => (
                  <tr key={p.id}>
                    <td className="mono">{p.sku}</td>
                    <td>{p.name}</td>
                    <td className="muted">{p.category ?? '—'}</td>
                    <td className="num-cell">{formatoCOP(p.unit_price)}</td>
                    <td className="num-cell">{formatoCOP(p.unit_cost)}</td>
                    <td className="num-cell">{formatoNum(p.stock)}</td>
                    <td>{p.is_active ? <StatusPill stock={p.stock} /> : <Pill>Inactivo</Pill>}</td>
                    <td>
                      <div className="row-gap" style={{ flexWrap: 'nowrap' }}>
                        <Button variant="ghost" iconOnly icon="editar" aria-label={`Editar ${p.name}`} onClick={() => abrir(p)} />
                        <Button variant="ghost" iconOnly icon="historial" aria-label={`Kardex de ${p.name}`} onClick={() => setKardex(p)} />
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      <Sheet abierto={!!editando} onCerrar={() => setEditando(null)} titulo={nuevo ? 'Nuevo producto' : 'Editar producto'} descripcion={nuevo ? 'El stock inicial genera un movimiento de entrada en el kardex.' : 'El stock solo cambia con movimientos de inventario.'}>
        <form className="form-grid" onSubmit={enviar}>
          <Field label="SKU" {...campo('sku')} disabled={!nuevo} required maxLength={50} />
          <Field label="Nombre" {...campo('name')} required maxLength={150} />
          <Field label="Categoría" {...campo('category')} list="categorias-lista" maxLength={100} />
          <datalist id="categorias-lista">{(categorias.data ?? []).map((c) => <option key={c} value={c} />)}</datalist>
          <div className="grid-2">
            <Field label="Precio de venta" type="number" min={1} step="any" {...campo('unit_price')} required />
            <Field label="Costo unitario" type="number" min={0} step="any" {...campo('unit_cost')} />
          </div>
          {nuevo && <Field label="Stock inicial" type="number" min={0} step={1} {...campo('stock')} />}
          {!nuevo && <label className="row-gap"><Switch checked={b.is_active} onChange={(v) => setB({ ...b, is_active: v })} label="Producto activo" /> Producto activo</label>}
          {error && <Alert tone="danger" title="No se pudo guardar" role="alert">{error}</Alert>}
          <div className="form-actions">
            <Button type="submit" icon="check" loading={guardar.isPending} disabled={!b.name || !b.unit_price || (nuevo && !b.sku)}>Guardar</Button>
            {!nuevo && <Button variant="secondary" loading={baja.isPending} onClick={() => baja.mutate((editando as Producto).id)}>Desactivar</Button>}
            <Button variant="ghost" onClick={() => setEditando(null)}>Cancelar</Button>
          </div>
        </form>
      </Sheet>

      <Sheet abierto={!!kardex} onCerrar={() => setKardex(null)} titulo={kardex ? `Kardex · ${kardex.name}` : ''} descripcion={kardex ? `${kardex.sku} · stock actual ${kardex.stock}` : undefined}>
        {kardex && <Kardex producto={kardex} />}
      </Sheet>
    </div>
  );
}
