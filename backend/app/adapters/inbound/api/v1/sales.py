from datetime import datetime

from fastapi import APIRouter, Depends, Query

from app.adapters.inbound.api.deps import servicio_ventas, usuario_actual
from app.adapters.inbound.schemas.ventas import VentaIn, VentaOut
from app.application.ventas import ServicioVentas

router = APIRouter(prefix="/sales", tags=["sales"], dependencies=[Depends(usuario_actual)])


@router.post("", response_model=VentaOut, status_code=201)
def registrar(datos: VentaIn, svc: ServicioVentas = Depends(servicio_ventas)):
    return svc.registrar([(i.product_id, i.quantity) for i in datos.items], datos.payment_method, datos.customer_id)


@router.get("", response_model=list[VentaOut])
def listar(desde: datetime | None = None, hasta: datetime | None = None, customer_id: int | None = None,
           limit: int = Query(50, ge=1, le=500), offset: int = Query(0, ge=0),
           svc: ServicioVentas = Depends(servicio_ventas)):
    return svc.listar(desde, hasta, customer_id, limit, offset)


@router.get("/{id}", response_model=VentaOut)
def obtener(id: int, svc: ServicioVentas = Depends(servicio_ventas)):
    return svc.obtener(id)
