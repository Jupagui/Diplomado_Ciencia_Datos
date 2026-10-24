import { SUGERENCIAS, type EstadoAsesor } from '../hooks/useAsesor';
import type { PlanAccion } from '../services/api';
import { Chip, Pill, RiesgoPill } from './Badges';
import { Button } from './Button';
import { ChatBubble, TypingDots } from './Chat';
import { Field } from './Inputs';
import { Alert } from './Surfaces';
import { vars } from './cls';

export function PlanVista({ plan }: { plan: PlanAccion }) {
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

/** Conversación completa con el asesor (historial, sugerencias y formulario). El estado viene de `useAsesor`. */
export function AsesorChat({ asesor }: { asesor: EstadoAsesor }) {
  const { chat, texto, setTexto, enviar, alEnviar, pendiente, fin } = asesor;
  return (
    <div className="chat">
      <div className="chat-log" aria-live="polite">
        {!chat.length && <ChatBubble rol="asistente">Hola. Pregúntame por inventario, combos, clientes o el calendario de festivos y te responderé con un plan de acción basado en tus datos.</ChatBubble>}
        {chat.map((m, i) => m.rol === 'usuario' ? <ChatBubble key={i} rol="usuario">{m.texto}</ChatBubble>
          : m.rol === 'error' ? <Alert key={i} tone="danger" title="El asesor no pudo responder" role="alert">{m.texto}</Alert>
          : <ChatBubble key={i} rol="asistente"><PlanVista plan={m.plan} /></ChatBubble>)}
        {pendiente && <TypingDots />}
        <div ref={fin} />
      </div>
      <div className="chat-sugg" role="group" aria-label="Preguntas sugeridas">
        {SUGERENCIAS.map((s) => <Chip key={s} disabled={pendiente} onClick={() => enviar(s)}>{s}</Chip>)}
      </div>
      <form className="chat-form" onSubmit={alEnviar}>
        <Field label="Tu pregunta" hideLabel icon="chat" placeholder="Escribe tu pregunta…" value={texto} onChange={(e) => setTexto(e.target.value)} maxLength={2000} />
        <Button type="submit" icon="enviar" loading={pendiente} disabled={!texto.trim()}>Preguntar</Button>
      </form>
    </div>
  );
}
