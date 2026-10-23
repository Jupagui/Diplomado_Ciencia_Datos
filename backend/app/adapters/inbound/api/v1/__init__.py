from fastapi import APIRouter

from app.adapters.inbound.api.v1 import advisor, analytics, auth, customers, etl, health, inventory, kpis, products, sales

api_router = APIRouter(prefix="/api/v1")
for modulo in (health, auth, products, customers, sales, inventory, kpis, etl, analytics, advisor):
    api_router.include_router(modulo.router)
