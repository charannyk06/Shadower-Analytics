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
]
