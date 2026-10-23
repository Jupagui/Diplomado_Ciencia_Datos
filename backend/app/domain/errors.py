"""Errores del dominio (sin dependencias de framework)."""


class ErrorDominio(Exception):
    def __init__(self, mensaje: str):
        super().__init__(mensaje)
        self.mensaje = mensaje


class NoEncontrado(ErrorDominio):
    pass


class ValidacionError(ErrorDominio):
    pass


class Conflicto(ErrorDominio):
    pass


class Duplicado(Conflicto):
    pass


class StockInsuficiente(Conflicto):
    pass


class CredencialesInvalidas(ErrorDominio):
    pass


class ErrorPipeline(ErrorDominio):
    """Fallo interno al ejecutar el ETL o entrenar modelos."""
