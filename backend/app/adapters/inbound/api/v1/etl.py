from fastapi import APIRouter, Depends, Query

from app.adapters.inbound.api.deps import servicio_analitica, usuario_actual
from app.adapters.inbound.schemas.analitica import EtlRunOut
from app.application.analitica import ServicioAnalitica

router = APIRouter(prefix="/etl", tags=["etl"], dependencies=[Depends(usuario_actual)])


@router.post("/run", response_model=EtlRunOut)
def ejecutar(force: bool = Query(False, description="Reentrenar aunque no haya ventas nuevas"),
             svc: ServicioAnalitica = Depends(servicio_analitica)):
    return svc.ejecutar_etl(force)


@router.get("/runs", response_model=list[EtlRunOut])
def runs(limit: int = Query(20, ge=1, le=200), svc: ServicioAnalitica = Depends(servicio_analitica)):
    return svc.listar_runs(limit)
