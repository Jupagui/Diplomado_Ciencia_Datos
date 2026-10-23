from fastapi import APIRouter, Depends, Query, Response

from app.adapters.inbound.api.deps import servicio_productos, usuario_actual
from app.adapters.inbound.schemas.productos import ProductoIn, ProductoOut, ProductoUpdate
from app.application.productos import ServicioProductos

router = APIRouter(prefix="/products", tags=["products"], dependencies=[Depends(usuario_actual)])


@router.get("", response_model=list[ProductoOut])
def listar(q: str | None = None, category: str | None = None, solo_activos: bool = False,
           limit: int = Query(200, ge=1, le=1000), offset: int = Query(0, ge=0),
           svc: ServicioProductos = Depends(servicio_productos)):
    return svc.listar(q, category, solo_activos, limit, offset)


@router.get("/categories", response_model=list[str])
def categorias(svc: ServicioProductos = Depends(servicio_productos)):
    return svc.categorias()


@router.get("/{id}", response_model=ProductoOut)
def obtener(id: int, svc: ServicioProductos = Depends(servicio_productos)):
    return svc.obtener(id)


@router.post("", response_model=ProductoOut, status_code=201)
def crear(datos: ProductoIn, svc: ServicioProductos = Depends(servicio_productos)):
    return svc.crear(**datos.model_dump())


@router.put("/{id}", response_model=ProductoOut)
def actualizar(id: int, datos: ProductoUpdate, svc: ServicioProductos = Depends(servicio_productos)):
    return svc.actualizar(id, datos.model_dump(exclude_unset=True))


@router.delete("/{id}", status_code=204)
def desactivar(id: int, svc: ServicioProductos = Depends(servicio_productos)):
    svc.desactivar(id)
    return Response(status_code=204)
