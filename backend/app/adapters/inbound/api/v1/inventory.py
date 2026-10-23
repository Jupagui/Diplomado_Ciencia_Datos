from fastapi import APIRouter, Depends, Query

from app.adapters.inbound.api.deps import servicio_inventario, usuario_actual
from app.adapters.inbound.schemas.inventario import MovimientoIn, MovimientoOut
from app.adapters.inbound.schemas.productos import ProductoOut
from app.application.inventario import ServicioInventario

router = APIRouter(prefix="/inventory", tags=["inventory"], dependencies=[Depends(usuario_actual)])


@router.get("/movements", response_model=list[MovimientoOut])
def kardex(product_id: int | None = None, movement_type: str | None = None,
           limit: int = Query(100, ge=1, le=1000), offset: int = Query(0, ge=0),
           svc: ServicioInventario = Depends(servicio_inventario)):
    return svc.listar(product_id, movement_type.upper() if movement_type else None, limit, offset)


@router.post("/movements", response_model=MovimientoOut, status_code=201)
def registrar(datos: MovimientoIn, svc: ServicioInventario = Depends(servicio_inventario)):
    return svc.registrar(**datos.model_dump())


@router.get("/low-stock", response_model=list[ProductoOut])
def stock_bajo(umbral: int = Query(10, ge=0), svc: ServicioInventario = Depends(servicio_inventario)):
    return svc.stock_bajo(umbral)
