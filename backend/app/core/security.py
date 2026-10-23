"""Hash de contraseñas (bcrypt) y JWT (PyJWT)."""
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.core.config import get_settings


def hashear_password(plano: str) -> str:
    return bcrypt.hashpw(plano.encode(), bcrypt.gensalt()).decode()


def verificar_password(plano: str, hash_: str) -> bool:
    try:
        return bcrypt.checkpw(plano.encode(), hash_.encode())
    except ValueError:
        return False


def crear_token(usuario: str) -> str:
    s = get_settings()
    exp = datetime.now(timezone.utc) + timedelta(minutes=s.jwt_expire_minutes)
    return jwt.encode({"sub": usuario, "exp": exp}, s.jwt_secret, algorithm=s.jwt_algorithm)


def decodificar_token(token: str) -> str | None:
    """Devuelve el usuario (sub) o None si el token es inválido o expiró."""
    s = get_settings()
    try:
        datos = jwt.decode(token, s.jwt_secret, algorithms=[s.jwt_algorithm])
    except jwt.PyJWTError:
        return None
    return datos.get("sub")
