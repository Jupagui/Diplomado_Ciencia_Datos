from fastapi import APIRouter, Depends, Query

from app.adapters.inbound.api.deps import servicio_kpis, usuario_actual
from app.adapters.inbound.schemas.kpis import ResumenKpis
from app.application.kpis import ServicioKpis

router = APIRouter(prefix="/kpis", tags=["kpis"], dependencies=[Depends(usuario_actual)])


@router.get("/resumen", response_model=ResumenKpis)
def resumen(dias: int = Query(30, ge=1, le=3650), top: int = Query(5, ge=1, le=50),
            svc: ServicioKpis = Depends(servicio_kpis)):
    return svc.resumen(dias, top)
