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
from openqilin.observability.metrics.recorder import configure_metrics
from openqilin.observability.tracing.tracer import configure_otel_logs, configure_tracer
from openqilin.shared_kernel.config import RuntimeSettings
from openqilin.shared_kernel.startup_validation import (
    enforce_connector_secret_hardening,
    verify_opa_bundle_loaded,
)


def create_control_plane_app() -> FastAPI:
    """Create the control-plane API app and register M1 ingress routes."""

    settings = RuntimeSettings()
    enforce_connector_secret_hardening(settings)
    if settings.opa_url:
        verify_opa_bundle_loaded(settings.opa_url)  # Fail fast if OPA unreachable

    # M12-WP5: Configure OTel export when otlp_endpoint is set.
    if settings.otlp_endpoint:
        configure_tracer(settings.otlp_endpoint)
        configure_metrics(settings.otlp_endpoint)
        configure_otel_logs(settings.otlp_endpoint)

    app = FastAPI(title="OpenQilin Control Plane", version="0.1.0")

    # M12-WP5: Instrument FastAPI with OTel spans when otlp_endpoint is set.
    if settings.otlp_endpoint:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

        FastAPIInstrumentor().instrument_app(app)

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
