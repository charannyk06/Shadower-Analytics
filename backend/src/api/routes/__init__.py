"""API routes for Shadow Analytics."""

from .executive import router as executive_router
from .agents import router as agents_router
from .users import router as users_router
from .workspaces import router as workspaces_router
from .metrics import router as metrics_router
from .exports import router as exports_router
from .reports import router as reports_router
from .health import router as health_router
from .websocket import router as websocket_router
from .user_activity import router as user_activity_router
from .credits import router as credits_router
from .errors import router as errors_router
from .trends import router as trends_router
from .leaderboards import router as leaderboards_router
from .funnels import router as funnels_router
from .materialized_views import router as materialized_views_router
from .moving_averages import router as moving_averages_router
from .anomalies import router as anomalies_router
from .dashboard import router as dashboard_router

__all__ = [
    "executive_router",
    "agents_router",
    "users_router",
    "workspaces_router",
    "metrics_router",
    "exports_router",
    "reports_router",
    "health_router",
    "websocket_router",
    "user_activity_router",
    "credits_router",
    "errors_router",
    "trends_router",
    "leaderboards_router",
    "funnels_router",
    "materialized_views_router",
    "moving_averages_router",
    "anomalies_router",
    "dashboard_router",
]
