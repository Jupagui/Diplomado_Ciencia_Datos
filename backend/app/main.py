"""Punto de entrada FastAPI: lifespan (create_all + admin + seed), CORS y rutas /api/v1."""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.adapters.inbound.api.deps import get_cipher
from app.adapters.inbound.api.errores import registrar_manejadores
from app.adapters.inbound.api.v1 import api_router
from app.adapters.outbound.persistence import models  # noqa: F401  (registra las tablas)
from app.adapters.outbound.persistence.repositories import UserRepoSQL
from app.core.config import get_settings
from app.core.db import Base, SessionLocal, engine
from app.core.security import hashear_password
from app.domain.entities import Usuario
from app.seed.generador_sintetico import base_vacia, sembrar

log = logging.getLogger("micronegocio")


@asynccontextmanager
async def lifespan(_: FastAPI):
    cfg = get_settings()
    Base.metadata.create_all(engine)
    with SessionLocal() as s:
        repo = UserRepoSQL(s)
        if repo.obtener_por_username(cfg.admin_user) is None:
            repo.crear(Usuario(cfg.admin_user, hashear_password(cfg.admin_password), True))
            s.commit()
            log.info("Usuario admin creado: %s", cfg.admin_user)
        if cfg.seed_on_empty and base_vacia(s):
            log.info("Base vacía: sembrando datos sintéticos...")
            log.info("Sembrado: %s", sembrar(s, get_cipher()))
    yield


app = FastAPI(title="Sistema de Gestión Operativa y Analítica para Micronegocios", version="1.0.0",
              lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=get_settings().cors_lista, allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])
registrar_manejadores(app)
app.include_router(api_router)
