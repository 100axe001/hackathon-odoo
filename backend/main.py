"""DealFlow360 API entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI

import app.models  # noqa: F401  registers every mapper before anything queries
from app.database.connection import Base, engine
from app.logging.setup_logging import get_logger, setup_logging
from app.routes.admin import router as admin_router
from app.routes.auth import router as auth_router

setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # No migrations by design: the schema is created from the models and the
    # demo data comes from seed.py. See AGENTS.md.
    Base.metadata.create_all(bind=engine)
    logger.info("Tables ready")
    yield


app = FastAPI(
    lifespan=lifespan,
    title="DealFlow360",
    description="Self-governing sales operations platform",
    version="0.1.0",
)

# Routers carry no prefix of their own, so the whole URL layout is visible here.
app.include_router(auth_router, prefix="/auth", tags=["Auth"])
app.include_router(admin_router, prefix="/admin", tags=["Admin"])

# No CORSMiddleware: the frontend reaches this through Vite's dev proxy, so
# every request is same-origin. Adding CORS would break the httpOnly cookie,
# which would then need SameSite=None; Secure and therefore HTTPS.


@app.get("/health", tags=["Health"])
def health():
    return {"success": True, "message": "DealFlow360 API is running", "data": None}
