"""DealFlow360 API entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy.exc import OperationalError

import app.models  # noqa: F401  registers every mapper before anything queries
from app.config.settings import settings
from app.database.connection import Base, engine
from app.logging.setup_logging import get_logger, setup_logging
from app.routes.admin import router as admin_router
from app.routes.approvals import router as approvals_router
from app.routes.auth import router as auth_router
from app.routes.dashboard import router as dashboard_router
from app.routes.deal_health import router as deal_health_router
from app.routes.fulfillment import router as fulfillment_router
from app.routes.invoices import router as invoices_router
from app.routes.portal import router as portal_router
from app.routes.products import router as products_router
from app.routes.quotation_approval import router as quotation_approval_router
from app.routes.quotation_fulfillment import router as quotation_fulfillment_router
from app.routes.quotations import router as quotations_router
from app.routes.reports import router as reports_router
from app.routes.subscriptions import router as subscriptions_router

setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # No migrations by design: the schema is created from the models and the
    # demo data comes from seed.py. See AGENTS.md.
    #
    # Fail loudly here rather than at the first query. The frontend falls back
    # to sample data when a read fails, so an unreachable database otherwise
    # looks like a working app until someone tries to save something.
    try:
        Base.metadata.create_all(bind=engine)
    except OperationalError as e:
        logger.error(
            "Cannot reach the database at %s - is `docker compose up -d` running? %s",
            settings.database_url.rsplit("@", 1)[-1],
            e.orig,
        )
        raise
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
app.include_router(quotations_router, prefix="/quotations", tags=["Quotations"])
app.include_router(quotation_approval_router, prefix="/quotations", tags=["Approvals"])
app.include_router(
    quotation_fulfillment_router, prefix="/quotations", tags=["Fulfillment"]
)
app.include_router(approvals_router, prefix="/approvals", tags=["Approvals"])
app.include_router(portal_router, prefix="/portal", tags=["Customer Portal"])
app.include_router(reports_router, prefix="/reports", tags=["Reports"])
app.include_router(admin_router, prefix="/admin", tags=["Admin"])
app.include_router(dashboard_router, prefix="/dashboard", tags=["Dashboard"])
app.include_router(products_router, prefix="/products", tags=["Products"])
app.include_router(deal_health_router, prefix="/deal-health", tags=["Deal Health"])
app.include_router(fulfillment_router, prefix="/fulfillment", tags=["Fulfillment"])
app.include_router(
    subscriptions_router, prefix="/subscriptions", tags=["Subscriptions"]
)
app.include_router(invoices_router, prefix="/invoices", tags=["Invoices"])

# No CORSMiddleware: the frontend reaches this through Vite's dev proxy, so
# every request is same-origin. Adding CORS would break the httpOnly cookie,
# which would then need SameSite=None; Secure and therefore HTTPS.


@app.get("/health", tags=["Health"])
def health():
    return {"success": True, "message": "DealFlow360 API is running", "data": None}
