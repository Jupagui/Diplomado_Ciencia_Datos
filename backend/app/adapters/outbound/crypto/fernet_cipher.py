"""Adaptador de cifrado simétrico con Fernet (AES-128-CBC + HMAC)."""
from cryptography.fernet import Fernet, InvalidToken


class FernetCipher:
    def __init__(self, clave: str | bytes):
        self._f = Fernet(clave)

    def cifrar(self, texto: str | None) -> str | None:
        if not texto:
            return None
        return self._f.encrypt(texto.encode()).decode()

    def descifrar(self, token: str | None) -> str | None:
        if not token:
            return None
        try:
            return self._f.decrypt(token.encode()).decode()
        except InvalidToken:
            return None
