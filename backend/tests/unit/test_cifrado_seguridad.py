import pytest
from cryptography.fernet import Fernet

from app.adapters.outbound.crypto.fernet_cipher import FernetCipher
from app.core.security import crear_token, decodificar_token, hashear_password, verificar_password


def test_fernet_ida_y_vuelta(cipher):
    token = cipher.cifrar("juan@example.com")
    assert token != "juan@example.com" and "juan" not in token
    assert cipher.descifrar(token) == "juan@example.com"


def test_fernet_unicode(cipher):
    assert cipher.descifrar(cipher.cifrar("Peña ñandú")) == "Peña ñandú"


@pytest.mark.parametrize("v", [None, ""])
def test_fernet_vacio(cipher, v):
    assert cipher.cifrar(v) is None
    assert cipher.descifrar(v) is None


def test_fernet_token_no_determinista(cipher):
    assert cipher.cifrar("a") != cipher.cifrar("a")


def test_fernet_clave_distinta_o_basura_devuelve_none(cipher):
    otro = FernetCipher(Fernet.generate_key())
    assert otro.descifrar(cipher.cifrar("secreto")) is None
    assert cipher.descifrar("no-es-un-token") is None


def test_password_hash():
    h = hashear_password("admin123")
    assert h != "admin123"
    assert verificar_password("admin123", h)
    assert not verificar_password("otra", h)
    assert not verificar_password("x", "hash-invalido")


def test_jwt_roundtrip_e_invalido():
    t = crear_token("admin")
    assert decodificar_token(t) == "admin"
    assert decodificar_token(t + "x") is None
    assert decodificar_token("basura") is None
