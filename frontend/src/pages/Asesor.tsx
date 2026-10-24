import { useAsesor } from '../hooks/useAsesor';
import { AsesorChat } from '../ui/AsesorChat';
import { Card, CardHeader } from '../ui/Surfaces';
import { vars } from '../ui/cls';

export default function Asesor() {
  const asesor = useAsesor();

  return (
    <div className="page">
      <header className="page-head">
        <p className="eyebrow rise" style={vars({ '--i': 0 })}>Asesor estratégico</p>
        <h1 className="title rise" style={vars({ '--i': 1 })}>Pregunta, <em>decide</em></h1>
        <p className="lead rise" style={vars({ '--i': 2 })}>Cada plan cita datos analíticos reales y pasa por guardrails: nunca propone descuentos superiores al 30 %.</p>
      </header>

      <Card className="asesor-chat rise" style={vars({ '--i': 3 })}>
        <CardHeader icon="chispa" title="Conversación" />
        <AsesorChat asesor={asesor} />
      </Card>
    </div>
  );
}
