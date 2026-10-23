from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.adapters.inbound.api.deps import usuario_actual
from app.adapters.inbound.schemas.auth import LoginIn, TokenOut
from app.adapters.outbound.persistence.repositories import UserRepoSQL
from app.core.db import get_session
from app.core.security import crear_token, verificar_password
from app.domain.errors import CredencialesInvalidas

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenOut)
def login(datos: LoginIn, s: Session = Depends(get_session)):
    u = UserRepoSQL(s).obtener_por_username(datos.username)
    if u is None or not verificar_password(datos.password, u.password_hash):
        raise CredencialesInvalidas("Usuario o contraseña incorrectos")
    return TokenOut(access_token=crear_token(u.username), username=u.username)


@router.get("/me")
def me(usuario: str = Depends(usuario_actual)):
    return {"username": usuario}
