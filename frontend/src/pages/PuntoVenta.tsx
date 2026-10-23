import { useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { estadoHttp, getClientes, getProductos, mensajeError, registrarVenta } from '../services/api';
import { Button } from '../ui/Button';
import { Icon } from '../ui/Icon';
import { Field, Select } from '../ui/Inputs';
import { Alert, Card, CardHeader, EmptyState, Skeleton } from '../ui/Surfaces';
import { vars } from '../ui/cls';
import { formatoCOP } from '../ui/format';
import { useToast } from '../ui/useToast';

const MEDIOS = ['EFECTIVO', 'TARJETA', 'NEQUI', 'TRANSFERENCIA'];

export default function PuntoVenta() {
  const qc = useQueryClient();
  const avisar = useToast();
  const [q, setQ] = useState('');
  const [carrito, setCarrito] = useState<Record<number, number>>({});
  const [cliente, setCliente] = useState('');
  const [medio, setMedio] = useState('EFECTIVO');
  const [error, setError] = useState<{ tono: 'warn' | 'danger'; texto: string } | null>(null);

  const productos = useQuery({ queryKey: ['productos', 'activos'], queryFn: () => getProductos({ solo_activos: true }) });
  const clientes = useQuery({ queryKey: ['clientes', '', false], queryFn: () => getClientes(undefined, false) });

  const lista = useMemo(() => {
    const t = q.trim().toLowerCase();
    return (productos.data ?? []).filter((p) => !t || p.name.toLowerCase().includes(t) || p.sku.toLowerCase().includes(t));
  }, [productos.data, q]);
  const porId = useMemo(() => new Map((productos.data ?? []).map((p) => [p.id, p])), [productos.data]);

  const lineas = Object.entries(carrito).map(([id, cant]) => ({ p: porId.get(Number(id))!, cant })).filter((l) => l.p);
  const total = lineas.reduce((s, l) => s + l.p.unit_price * l.cant, 0);

  const cambiar = (id: number, delta: number) => {
    setError(null);
    setCarrito((c) => {
      const p = porId.get(id);
      const nueva = Math.min((c[id] ?? 0) + delta, p?.stock ?? 0);
      const sig = { ...c };
      if (nueva <= 0) delete sig[id];
      else sig[id] = nueva;
      return sig;
    });
  };

  const venta = useMutation({
    mutationFn: () => registrarVenta({
      items: lineas.map((l) => ({ product_id: l.p.id, quantity: l.cant })),
      payment_method: medio,
      customer_id: cliente ? Number(cliente) : null,
    }),
    onSuccess: (v) => {
      avisar(`Venta #${v.id} registrada por ${formatoCOP(v.total_amount)}`, 'ok');
      setCarrito({});
      setCliente('');
      setError(null);
      void qc.invalidateQueries({ queryKey: ['productos'] });
      void qc.invalidateQueries({ queryKey: ['kpis'] });
      void qc.invalidateQueries({ queryKey: ['stock-bajo'] });
    },
    onError: (e) => {
      setError({ tono: estadoHttp(e) === 409 ? 'warn' : 'danger', texto: mensajeError(e) });
      // El stock pudo cambiar: se refresca para mostrar lo disponible
      void qc.invalidateQueries({ queryKey: ['productos'] });
    },
  });

  return (
    <div className="page">
      <header className="page-head">
        <p className="eyebrow rise" style={vars({ '--i': 0 })}>Punto de venta</p>
        <h1 className="title rise" style={vars({ '--i': 1 })}>Registrar una <em>venta</em></h1>
      </header>

      <div className="pos">
        <Card className="rise" style={vars({ '--i': 2 })}>
          <CardHeader icon="caja" title="Productos" />
          <Field label="Buscar producto" hideLabel icon="buscar" placeholder="Buscar por nombre o SKU…" value={q} onChange={(e) => setQ(e.target.value)} />
          <div style={{ height: 'var(--sp-2)' }} />
          {productos.isLoading ? <Skeleton ancho="100%" /> : !lista.length ? <EmptyState icon="buscar" title="Sin resultados">Prueba con otro nombre o SKU.</EmptyState> : (
            <div className="prod-grid">
              {lista.map((p) => (
                <button key={p.id} type="button" className="prod-tile" disabled={p.stock <= 0} onClick={() => cambiar(p.id, 1)} aria-label={`Agregar ${p.name}`}>
                  <b>{p.name}</b>
                  <span>{p.sku} · {p.stock > 0 ? `${p.stock} disp.` : 'Agotado'}</span>
                  <span className="price">{formatoCOP(p.unit_price)}</span>
                </button>
              ))}
            </div>
          )}
        </Card>

        <Card feature className="cart rise" style={vars({ '--i': 3 })}>
          <CardHeader icon="carrito" title="Carrito" aside={<span className="muted small">{lineas.length} ítems</span>} />
          {!lineas.length ? <EmptyState icon="carrito" title="Carrito vacío">Toca un producto para agregarlo.</EmptyState> : (
            <div className="cart-lines">
              {lineas.map(({ p, cant }) => (
                <div key={p.id} className="cart-line">
                  <div><b>{p.name}</b><small>{formatoCOP(p.unit_price)} c/u</small></div>
                  <div className="qty">
                    <button type="button" aria-label={`Quitar una unidad de ${p.name}`} onClick={() => cambiar(p.id, -1)}><Icon name="cerrar" /></button>
                    <output aria-label="Cantidad">{cant}</output>
                    <button type="button" aria-label={`Agregar una unidad de ${p.name}`} onClick={() => cambiar(p.id, 1)} disabled={cant >= p.stock}><Icon name="mas" /></button>
                  </div>
                  <b className="num-cell">{formatoCOP(p.unit_price * cant)}</b>
                </div>
              ))}
            </div>
          )}
          <div style={{ height: 'var(--sp-2)' }} />
          <div className="stack">
            <Select label="Cliente (opcional)" value={cliente} onChange={(e) => setCliente(e.target.value)}>
              <option value="">Venta de mostrador (sin cliente)</option>
              {(clientes.data ?? []).map((c) => <option key={c.id} value={c.id}>{c.first_name} {c.last_name}</option>)}
            </Select>
            <Select label="Método de pago" value={medio} onChange={(e) => setMedio(e.target.value)}>
              {MEDIOS.map((m) => <option key={m} value={m}>{m.charAt(0) + m.slice(1).toLowerCase()}</option>)}
            </Select>
            {error && <Alert tone={error.tono} title={error.tono === 'warn' ? 'Stock insuficiente' : 'No se pudo registrar la venta'} role="alert">{error.texto}</Alert>}
            <div className="cart-total"><span>Total</span><span>{formatoCOP(total)}</span></div>
            <Button icon="check" loading={venta.isPending} disabled={!lineas.length} onClick={() => venta.mutate()}>Confirmar venta</Button>
            {!!lineas.length && <Button variant="ghost" onClick={() => { setCarrito({}); setError(null); }}>Vaciar carrito</Button>}
          </div>
        </Card>
      </div>
    </div>
  );
}
