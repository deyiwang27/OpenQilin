"""Control-plane FastAPI application assembly."""

from fastapi import FastAPI

from openqilin.control_plane.api.dependencies import build_runtime_services
from openqilin.control_plane.routers.discord_ingress import router as discord_ingress_router
from openqilin.control_plane.routers.governance import router as governance_router
from openqilin.control_plane.routers.owner_commands import router as owner_commands_router
from openqilin.control_plane.routers.owner_discussions import (
    router as owner_discussions_router,
)
from openqilin.control_plane.routers.queries import router as queries_router


def create_control_plane_app() -> FastAPI:
    """Create the control-plane API app and register M1 ingress routes."""

    app = FastAPI(title="OpenQilin Control Plane", version="0.1.0")

    @app.get("/health/live", tags=["health"])
    def health_live() -> dict[str, str]:
        """Liveness probe for container orchestration health checks."""

        return {"status": "live"}

    @app.get("/health/ready", tags=["health"])
    def health_ready() -> dict[str, str]:
        """Readiness probe once runtime services are initialized."""

        return {"status": "ready"}

    app.state.runtime_services = build_runtime_services()
    app.include_router(owner_commands_router)
    app.include_router(queries_router)
    app.include_router(owner_discussions_router)
    app.include_router(governance_router)
    app.include_router(discord_ingress_router)
    return app


app = create_control_plane_app()
