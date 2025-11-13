"""API versioning system.

Manages multiple API versions and provides backwards compatibility.
"""

from fastapi import APIRouter, HTTPException, status
from typing import Dict, Optional, Callable
import logging

logger = logging.getLogger(__name__)


class VersionedAPI:
    """Manages multiple API versions.

    Allows registering different versions of the API and
    routing requests to the appropriate version.
    """

    def __init__(self, default_version: str = "v1"):
        """Initialize versioned API.

        Args:
            default_version: Default version to use if none specified
        """
        self.versions: Dict[str, APIRouter] = {}
        self.default_version = default_version
        self.deprecated_versions: set = set()

    def register_version(
        self,
        version: str,
        router: APIRouter,
        deprecated: bool = False
    ):
        """Register an API version.

        Args:
            version: Version identifier (e.g., "v1", "v2")
            router: FastAPI router for this version
            deprecated: Whether this version is deprecated
        """
        self.versions[version] = router

        if deprecated:
            self.deprecated_versions.add(version)
            logger.warning(f"API version {version} is registered as deprecated")

        logger.info(f"Registered API version: {version}")

    def get_router(self, version: str) -> APIRouter:
        """Get router for specific version.

        Args:
            version: Version identifier

        Returns:
            APIRouter for the specified version

        Raises:
            HTTPException: If version doesn't exist
        """
        if version not in self.versions:
            # Try to fallback to default version
            if self.default_version in self.versions:
                logger.warning(
                    f"Version {version} not found, falling back to {self.default_version}"
                )
                return self.versions[self.default_version]

            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"API version {version} not found"
            )

        if version in self.deprecated_versions:
            logger.warning(
                f"Client using deprecated API version: {version}"
            )

        return self.versions[version]

    def get_all_versions(self) -> list:
        """Get list of all registered versions."""
        return list(self.versions.keys())

    def is_deprecated(self, version: str) -> bool:
        """Check if a version is deprecated."""
        return version in self.deprecated_versions

    def mark_deprecated(self, version: str):
        """Mark a version as deprecated.

        Args:
            version: Version to mark as deprecated
        """
        if version in self.versions:
            self.deprecated_versions.add(version)
            logger.info(f"Marked API version {version} as deprecated")
        else:
            raise ValueError(f"Version {version} not registered")


# Global versioned API instance
versioned_api = VersionedAPI(default_version="v1")


# Version-specific routers
v1_router = APIRouter(prefix="/api/v1", tags=["v1"])
v2_router = APIRouter(prefix="/api/v2", tags=["v2"])


def version_router(version: str) -> Callable:
    """Decorator to register routes for a specific API version.

    Usage:
        @version_router("v1")
        def setup_v1_routes(router: APIRouter):
            @router.get("/example")
            async def example():
                return {"version": "v1"}

    Args:
        version: API version identifier
    """
    def decorator(func: Callable):
        def wrapper():
            router = APIRouter()
            func(router)
            versioned_api.register_version(version, router)
            return router
        return wrapper
    return decorator


def get_api_version_info() -> dict:
    """Get information about all API versions."""
    versions = []

    for version in versioned_api.get_all_versions():
        versions.append({
            "version": version,
            "deprecated": versioned_api.is_deprecated(version),
            "url": f"/api/{version}"
        })

    return {
        "current_version": versioned_api.default_version,
        "versions": versions,
        "deprecated_versions": list(versioned_api.deprecated_versions)
    }


@v1_router.get("/version")
async def get_version_v1():
    """Get API version information (v1)."""
    return {
        "version": "1.0.0",
        "api_version": "v1",
        "status": "stable"
    }


# Register v1 router
versioned_api.register_version("v1", v1_router, deprecated=False)
