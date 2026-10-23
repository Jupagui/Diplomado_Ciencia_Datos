import { useEffect, useRef, useState, type FormEvent } from 'react';
import { useMutation } from '@tanstack/react-query';
import { mensajeError, preguntarAsesor, type PlanAccion } from '../services/api';
import { Chip, Pill, RiesgoPill } from '../ui/Badges';
import { Button } from '../ui/Button';
import { ChatBubble, TypingDots } from '../ui/Chat';
import { Field } from '../ui/Inputs';
import { Alert, Card, CardHeader } from '../ui/Surfaces';
import { vars } from '../ui/cls';

type Mensaje = { rol: 'usuario'; texto: string } | { rol: 'asistente'; plan: PlanAccion } | { rol: 'error'; texto: string };

const SUGERENCIAS = [
  '¿Qué debo reponer esta semana?',
  '¿Qué combos puedo armar para subir el ticket?',
  '¿Cómo fidelizo a mis mejores clientes?',
  'Prepárame para el próximo festivo',
  '¿Dónde puedo proteger mi margen?',
];

function PlanVista({ plan }: { plan: PlanAccion }) {
  return (
    <div className="plan">
      <div className="plan-head">
        <Pill tone={plan.modo === 'gemini' ? 'info' : 'neutral'}>{plan.modo === 'gemini' ? 'Gemini' : 'Simulado'}</Pill>
        <span className="muted small">{plan.acciones.length} acciones propuestas</span>
      </div>
      <p className="plan-summary">{plan.resumen}</p>
      <div className="plan-actions">
        {plan.acciones.map((a, i) => (
          <article key={i} className="plan-card rise" style={vars({ '--i': i })}>
            <div className="plan-head"><RiesgoPill riesgo={a.riesgo} />{a.descuento_pct != null && <Pill tone="gold">Descuento {a.descuento_pct}%</Pill>}</div>
            <h4>{a.accion}</h4>
            <p>{a.justificacion}</p>
            <p><b>Impacto:</b> {a.impacto_estimado}</p>
            <ul aria-label="Datos citados">{a.datos_citados.map((d, j) => <li key={j}>{d}</li>)}</ul>
          </article>
        ))}
      </div>
      {plan.advertencias.length > 0 && (
        <Alert tone="warn" title="Advertencias">
          <ul>{plan.advertencias.map((w, i) => <li key={i}>{w}</li>)}</ul>
        </Alert>
      )}
    </div>
  );
}

export default function Asesor() {
  const [chat, setChat] = useState<Mensaje[]>([]);
  const [texto, setTexto] = useState('');
  const fin = useRef<HTMLDivElement>(null);

  const preguntar = useMutation({
    mutationFn: preguntarAsesor,
    onSuccess: (plan) => setChat((c) => [...c, { rol: 'asistente', plan }]),
    onError: (e) => setChat((c) => [...c, { rol: 'error', texto: mensajeError(e) }]),
  });

  useEffect(() => { fin.current?.scrollIntoView({ block: 'nearest', behavior: 'smooth' }); }, [chat, preguntar.isPending]);

  const enviar = (pregunta: string) => {
    const p = pregunta.trim();
    if (!p || preguntar.isPending) return;
    setChat((c) => [...c, { rol: 'usuario', texto: p }]);
    setTexto('');
    preguntar.mutate(p);
  };
  const alEnviar = (e: FormEvent) => { e.preventDefault(); enviar(texto); };

  return (
    <div className="page">
      <header className="page-head">
        <p className="eyebrow rise" style={vars({ '--i': 0 })}>Asesor estratégico</p>
        <h1 className="title rise" style={vars({ '--i': 1 })}>Pregunta, <em>decide</em></h1>
        <p className="lead rise" style={vars({ '--i': 2 })}>Cada plan cita datos analíticos reales y pasa por guardrails: nunca propone descuentos superiores al 30 %.</p>
      </header>

      <Card className="asesor-chat rise" style={vars({ '--i': 3 })}>
        <CardHeader icon="chispa" title="Conversación" />
        <div className="chat">
          <div className="chat-log" aria-live="polite">
            {!chat.length && <ChatBubble rol="asistente">Hola. Pregúntame por inventario, combos, clientes o el calendario de festivos y te responderé con un plan de acción basado en tus datos.</ChatBubble>}
            {chat.map((m, i) => m.rol === 'usuario' ? <ChatBubble key={i} rol="usuario">{m.texto}</ChatBubble>
              : m.rol === 'error' ? <Alert key={i} tone="danger" title="El asesor no pudo responder" role="alert">{m.texto}</Alert>
              : <ChatBubble key={i} rol="asistente"><PlanVista plan={m.plan} /></ChatBubble>)}
            {preguntar.isPending && <TypingDots />}
            <div ref={fin} />
          </div>
          <div className="chat-sugg" role="group" aria-label="Preguntas sugeridas">
            {SUGERENCIAS.map((s) => <Chip key={s} disabled={preguntar.isPending} onClick={() => enviar(s)}>{s}</Chip>)}
          </div>
          <form className="chat-form" onSubmit={alEnviar}>
            <Field label="Tu pregunta" hideLabel icon="chat" placeholder="Escribe tu pregunta…" value={texto} onChange={(e) => setTexto(e.target.value)} maxLength={2000} />
            <Button type="submit" icon="enviar" loading={preguntar.isPending} disabled={!texto.trim()}>Preguntar</Button>
          </form>
        </div>
      </Card>
    </div>
  );
}
