"""Casos de uso de clientes. La PII se cifra al guardar y se enmascara por defecto al leer."""
from dataclasses import dataclass
from datetime import datetime

from app.domain.entities import Cliente
from app.domain.errors import Conflicto, NoEncontrado, ValidacionError
from app.domain.ports import CipherPort, CustomerRepo, Transaccion


@dataclass
class ClienteVista:
    id: int
    first_name: str
    last_name: str
    email: str | None
    phone: str | None
    revelado: bool
    created_at: datetime | None


def enmascarar_email(email: str | None) -> str | None:
    if not email:
        return None
    usuario, _, dominio = email.partition("@")
    return f"{usuario[:1]}***@{dominio}" if dominio else "***"


def enmascarar_telefono(tel: str | None) -> str | None:
    if not tel:
        return None
    return "*" * max(len(tel) - 3, 0) + tel[-3:]


class ServicioClientes:
    def __init__(self, repo: CustomerRepo, cipher: CipherPort, tx: Transaccion):
        self.repo = repo
        self.cipher = cipher
        self.tx = tx

    def _vista(self, c: Cliente, revelar: bool) -> ClienteVista:
        email = self.cipher.descifrar(c.encrypted_email)
        tel = self.cipher.descifrar(c.encrypted_phone)
        if not revelar:
            email, tel = enmascarar_email(email), enmascarar_telefono(tel)
        return ClienteVista(c.id, c.first_name, c.last_name, email, tel, revelar, c.created_at)

    def _obtener(self, id: int) -> Cliente:
        c = self.repo.obtener(id)
        if c is None:
            raise NoEncontrado(f"Cliente {id} no existe")
        return c

    def listar(self, q=None, limit=100, offset=0, revelar=False) -> list[ClienteVista]:
        return [self._vista(c, revelar) for c in self.repo.listar(q, limit, offset)]

    def obtener(self, id: int, revelar=False) -> ClienteVista:
        return self._vista(self._obtener(id), revelar)

    def crear(self, first_name: str, last_name: str, email: str | None = None, phone: str | None = None,
              revelar=False) -> ClienteVista:
        if not first_name.strip() or not last_name.strip():
            raise ValidacionError("Nombre y apellido son obligatorios")
        if email and "@" not in email:
            raise ValidacionError("Email inválido")
        c = self.repo.crear(Cliente(first_name.strip(), last_name.strip(),
                                    self.cipher.cifrar(email), self.cipher.cifrar(phone)))
        self.tx.commit()
        return self._vista(c, revelar)

    def actualizar(self, id: int, first_name=None, last_name=None, email=None, phone=None,
                   revelar=False) -> ClienteVista:
        self._obtener(id)
        cambios: dict = {}
        if first_name is not None:
            cambios["first_name"] = first_name.strip()
        if last_name is not None:
            cambios["last_name"] = last_name.strip()
        if email is not None:
            if email and "@" not in email:
                raise ValidacionError("Email inválido")
            cambios["encrypted_email"] = self.cipher.cifrar(email or None)
        if phone is not None:
            cambios["encrypted_phone"] = self.cipher.cifrar(phone or None)
        c = self.repo.actualizar(id, cambios)
        self.tx.commit()
        return self._vista(c, revelar)

    def eliminar(self, id: int) -> None:
        self._obtener(id)
        if self.repo.tiene_ventas(id):
            raise Conflicto("El cliente tiene ventas asociadas y no puede eliminarse")
        self.repo.eliminar(id)
        self.tx.commit()
