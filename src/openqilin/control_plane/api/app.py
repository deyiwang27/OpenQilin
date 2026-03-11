"""Control-plane FastAPI application assembly."""

from fastapi import FastAPI

from openqilin.control_plane.api.dependencies import build_runtime_services
from openqilin.control_plane.routers.owner_commands import router as owner_commands_router


def create_control_plane_app() -> FastAPI:
    """Create the control-plane API app and register M1 ingress routes."""

    app = FastAPI(title="OpenQilin Control Plane", version="0.1.0")
    app.state.runtime_services = build_runtime_services()
    app.include_router(owner_commands_router)
    return app


app = create_control_plane_app()
