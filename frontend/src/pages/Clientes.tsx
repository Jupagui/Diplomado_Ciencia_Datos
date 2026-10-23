import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { getClientes, mensajeError } from '../services/api';
import { Pill } from '../ui/Badges';
import { Button } from '../ui/Button';
import { Field } from '../ui/Inputs';
import { Alert, Card, CardHeader, EmptyState, Skeleton } from '../ui/Surfaces';
import { vars } from '../ui/cls';
import { formatoFecha } from '../ui/format';

export default function Clientes() {
  const [q, setQ] = useState('');
  const [revelar, setRevelar] = useState(false);
  const clientes = useQuery({ queryKey: ['clientes', q, revelar], queryFn: () => getClientes(q, revelar) });

  return (
    <div className="page">
      <header className="page-head">
        <p className="eyebrow rise" style={vars({ '--i': 0 })}>Datos personales protegidos</p>
        <h1 className="title rise" style={vars({ '--i': 1 })}>Tus <em>clientes</em></h1>
        <p className="lead rise" style={vars({ '--i': 2 })}>El correo y el teléfono se guardan cifrados (Fernet) y la API los devuelve enmascarados por defecto.</p>
      </header>

      <Card className="rise" style={vars({ '--i': 3 })}>
        <CardHeader icon="usuarios" title="Clientes" aside={
          <Button variant={revelar ? 'primary' : 'secondary'} icon="ojo" onClick={() => setRevelar((r) => !r)} aria-pressed={revelar}>
            {revelar ? 'Ocultar datos' : 'Revelar datos'}
          </Button>
        } />
        <div className="toolbar" style={{ marginBottom: 'var(--sp-2)' }}>
          <Field label="Buscar cliente" hideLabel icon="buscar" placeholder="Buscar por nombre o apellido…" value={q} onChange={(e) => setQ(e.target.value)} />
          <Pill tone={revelar ? 'warn' : 'ok'}>{revelar ? 'PII visible' : 'PII enmascarada'}</Pill>
        </div>
        {clientes.isError && <Alert tone="danger" title="No se pudieron cargar los clientes" role="alert">{mensajeError(clientes.error)}</Alert>}
        {clientes.isLoading ? <Skeleton ancho="100%" /> : !clientes.data?.length ? <EmptyState icon="usuarios" title="Sin clientes" /> : (
          <div className="tbl-wrap">
            <table className="tbl">
              <thead><tr><th>Cliente</th><th>Correo</th><th>Teléfono</th><th>Alta</th></tr></thead>
              <tbody>
                {clientes.data.map((c) => (
                  <tr key={c.id}>
                    <td>{c.first_name} {c.last_name}</td>
                    <td className="mono">{c.email ?? '—'}</td>
                    <td className="mono">{c.phone ?? '—'}</td>
                    <td className="muted">{formatoFecha(c.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}
