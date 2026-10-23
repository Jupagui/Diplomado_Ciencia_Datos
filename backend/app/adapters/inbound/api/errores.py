"""Traduce errores del dominio a respuestas HTTP."""
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.domain.errors import Conflicto, CredencialesInvalidas, ErrorDominio, ErrorPipeline, NoEncontrado, ValidacionError


def registrar_manejadores(app: FastAPI) -> None:
    def make(status: int, headers: dict | None = None):
        async def handler(_: Request, exc: ErrorDominio):
            return JSONResponse(status_code=status, content={"detail": exc.mensaje}, headers=headers)
        return handler

    app.add_exception_handler(ErrorPipeline, make(500))
    app.add_exception_handler(NoEncontrado, make(404))
    app.add_exception_handler(ValidacionError, make(422))
    app.add_exception_handler(Conflicto, make(409))
    app.add_exception_handler(CredencialesInvalidas, make(401, {"WWW-Authenticate": "Bearer"}))
