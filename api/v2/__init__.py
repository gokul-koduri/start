"""API v2 routers."""

from api.v2.government import router as government_router
from api.v2.opportunities import router as opportunities_router
from api.v2.signals import router as signals_router
from api.v2.webhooks import router as webhooks_router
from api.v2.export import router as export_router
from api.v2.watchlists import router as watchlists_router
from api.v2.apis import router as apis_router
from api.v2.endpoints import router as endpoints_router
from api.v2.organizations import router as organizations_router
from api.v2.scanner import router as scanner_router
from api.v2.stats import router as stats_router

__all__ = [
    "government_router",
    "opportunities_router",
    "signals_router",
    "webhooks_router",
    "export_router",
    "watchlists_router",
    "apis_router",
    "endpoints_router",
    "organizations_router",
    "scanner_router",
    "stats_router",
]
