"""
Sygnode Core Engine v2.0 — FastAPI Application.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.settings import settings
from app.database import engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    # Startup: verify DB connection
    async with engine.begin() as conn:
        pass  # Connection pool is initialized
    yield
    # Shutdown: cleanup
    await engine.dispose()
    from app.services.document_service import document_service
    await document_service.close()
    from app.services.cf_adapter import cf_adapter
    await cf_adapter.close()


app = FastAPI(
    title="Sygnode Core Engine",
    version="2.0.0",
    description="Plataforma de procurement B2B con trazabilidad y IA",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Register routers ---
from app.routers.health import router as health_router
from app.routers.auth import router as auth_router
from app.routers.intake import router as intake_router
from app.routers.rfqs import router as rfqs_router
from app.routers.cotizaciones import router as cotizaciones_router
from app.routers.quotes import router as quotes_router
from app.routers.cases import router as cases_router
from app.routers.suppliers import router as suppliers_router
from app.routers.clients import router as clients_router
from app.routers.freight import router as freight_router
from app.routers.validations import router as validations_router
from app.routers.ml import router as ml_router
from app.routers.webhook import router as webhook_router
from app.routers.public import router as public_router

# All routes under /api/v2 except public and webhook
PREFIX = "/api/v2"

app.include_router(health_router, prefix=PREFIX)
app.include_router(auth_router, prefix=PREFIX)
app.include_router(intake_router, prefix=PREFIX)
app.include_router(rfqs_router, prefix=PREFIX)
app.include_router(cotizaciones_router, prefix=PREFIX)
app.include_router(quotes_router, prefix=PREFIX)
app.include_router(cases_router, prefix=PREFIX)
app.include_router(suppliers_router, prefix=PREFIX)
app.include_router(clients_router, prefix=PREFIX)
app.include_router(freight_router, prefix=PREFIX)
app.include_router(validations_router, prefix=PREFIX)
app.include_router(ml_router, prefix=PREFIX)
app.include_router(webhook_router, prefix=PREFIX)
app.include_router(public_router, prefix=PREFIX)
