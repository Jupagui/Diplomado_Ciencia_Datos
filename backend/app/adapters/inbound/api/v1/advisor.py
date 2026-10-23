from fastapi import APIRouter, Depends

from app.adapters.inbound.api.deps import servicio_asesor, usuario_actual
from app.adapters.inbound.schemas.analitica import PreguntaIn
from app.application.asesor import ServicioAsesor
from app.domain.plan_accion import PlanAccion

router = APIRouter(prefix="/advisor", tags=["advisor"], dependencies=[Depends(usuario_actual)])


@router.post("/ask", response_model=PlanAccion)
def preguntar(datos: PreguntaIn, svc: ServicioAsesor = Depends(servicio_asesor)):
    return svc.preguntar(datos.pregunta)
