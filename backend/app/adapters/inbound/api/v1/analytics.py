from fastapi import APIRouter, Depends, Query

from app.adapters.inbound.api.deps import servicio_analitica, usuario_actual
from app.adapters.inbound.schemas.analitica import DemandaProductoOut, MetricasOut, ReglaOut, SegmentosOut
from app.application.analitica import ServicioAnalitica

router = APIRouter(prefix="/analytics", tags=["analytics"], dependencies=[Depends(usuario_actual)])


@router.get("/demand", response_model=list[DemandaProductoOut])
def demanda(horizon: int = 7, product_id: int | None = None,
            svc: ServicioAnalitica = Depends(servicio_analitica)):
    return svc.demanda(horizon, product_id)


@router.get("/basket", response_model=list[ReglaOut])
def canasta(limit: int = Query(100, ge=1, le=500), svc: ServicioAnalitica = Depends(servicio_analitica)):
    return svc.reglas(limit)


@router.get("/segments", response_model=SegmentosOut)
def segmentos(svc: ServicioAnalitica = Depends(servicio_analitica)):
    return svc.segmentos()


@router.get("/metrics", response_model=MetricasOut)
def metricas(svc: ServicioAnalitica = Depends(servicio_analitica)):
    return svc.metricas()
