"""Composición: arma los casos de uso con sus adaptadores (inyección de dependencias)."""
from functools import lru_cache

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.adapters.outbound.crypto.fernet_cipher import FernetCipher
from app.adapters.outbound.persistence import repositories as r
from app.adapters.outbound.llm.gemini_advisor import GeminiAdvisor
from app.adapters.outbound.llm.mock_advisor import MockAdvisor
from app.adapters.outbound.persistence.analytics_repositories import AnalyticsRepoSQL, EtlRunRepoSQL, EtlSourceSQL
from app.application.analitica import ServicioAnalitica
from app.application.asesor import ServicioAsesor
from app.application.clientes import ServicioClientes
from app.application.inventario import ServicioInventario
from app.application.kpis import ServicioKpis
from app.application.productos import ServicioProductos
from app.application.ventas import ServicioVentas
from app.core.config import get_settings, obtener_clave_fernet
from app.core.db import get_session
from app.core.security import decodificar_token
from app.domain.errors import CredencialesInvalidas
from app.etl.pipeline import ConfigAnalitica, PipelineETL

_bearer = HTTPBearer(auto_error=False)


@lru_cache
def get_cipher() -> FernetCipher:
    return FernetCipher(obtener_clave_fernet())


def usuario_actual(cred: HTTPAuthorizationCredentials | None = Depends(_bearer)) -> str:
    if cred is None:
        raise CredencialesInvalidas("Falta el token de autenticación")
    usuario = decodificar_token(cred.credentials)
    if usuario is None:
        raise CredencialesInvalidas("Token inválido o expirado")
    return usuario


def servicio_productos(s: Session = Depends(get_session)) -> ServicioProductos:
    return ServicioProductos(r.ProductRepoSQL(s), r.InventoryRepoSQL(s), s)


def servicio_clientes(s: Session = Depends(get_session), cipher=Depends(get_cipher)) -> ServicioClientes:
    return ServicioClientes(r.CustomerRepoSQL(s), cipher, s)


def servicio_ventas(s: Session = Depends(get_session)) -> ServicioVentas:
    return ServicioVentas(r.SaleRepoSQL(s), r.ProductRepoSQL(s), r.CustomerRepoSQL(s), r.InventoryRepoSQL(s), s)


def servicio_inventario(s: Session = Depends(get_session)) -> ServicioInventario:
    return ServicioInventario(r.InventoryRepoSQL(s), r.ProductRepoSQL(s), s)


def servicio_kpis(s: Session = Depends(get_session)) -> ServicioKpis:
    return ServicioKpis(r.KpiRepoSQL(s))


def servicio_analitica(s: Session = Depends(get_session), cipher=Depends(get_cipher)) -> ServicioAnalitica:
    cfg = get_settings()
    runs, analytics = EtlRunRepoSQL(s), AnalyticsRepoSQL(s)
    pipeline = PipelineETL(EtlSourceSQL(s), runs, analytics, cipher, s, ConfigAnalitica(
        cfg.apriori_min_support, cfg.apriori_min_confidence, cfg.apriori_min_lift, cfg.demanda_test_dias))
    return ServicioAnalitica(pipeline, runs, analytics)


def get_advisor():
    """Gemini si hay GEMINI_API_KEY; si no, asesor simulado."""
    cfg = get_settings()
    if cfg.gemini_api_key:
        return GeminiAdvisor(cfg.gemini_api_key, cfg.gemini_model)
    return MockAdvisor()


def servicio_asesor(analitica: ServicioAnalitica = Depends(servicio_analitica),
                    kpis: ServicioKpis = Depends(servicio_kpis), advisor=Depends(get_advisor)) -> ServicioAsesor:
    return ServicioAsesor(advisor, MockAdvisor(), analitica, kpis)
