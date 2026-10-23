from fastapi import APIRouter, Depends, Query, Response

from app.adapters.inbound.api.deps import servicio_clientes, usuario_actual
from app.adapters.inbound.schemas.clientes import ClienteIn, ClienteOut, ClienteUpdate
from app.application.clientes import ServicioClientes

router = APIRouter(prefix="/customers", tags=["customers"], dependencies=[Depends(usuario_actual)])


@router.get("", response_model=list[ClienteOut])
def listar(q: str | None = None, revelar: bool = False, limit: int = Query(100, ge=1, le=1000),
           offset: int = Query(0, ge=0), svc: ServicioClientes = Depends(servicio_clientes)):
    return svc.listar(q, limit, offset, revelar)


@router.get("/{id}", response_model=ClienteOut)
def obtener(id: int, revelar: bool = False, svc: ServicioClientes = Depends(servicio_clientes)):
    return svc.obtener(id, revelar)


@router.post("", response_model=ClienteOut, status_code=201)
def crear(datos: ClienteIn, svc: ServicioClientes = Depends(servicio_clientes)):
    return svc.crear(**datos.model_dump())


@router.put("/{id}", response_model=ClienteOut)
def actualizar(id: int, datos: ClienteUpdate, svc: ServicioClientes = Depends(servicio_clientes)):
    return svc.actualizar(id, **datos.model_dump(exclude_unset=True))


@router.delete("/{id}", status_code=204)
def eliminar(id: int, svc: ServicioClientes = Depends(servicio_clientes)):
    svc.eliminar(id)
    return Response(status_code=204)
