"""FastAPI entrypoint for the OpenQilin control-plane API."""

from fastapi import FastAPI

from openqilin.control_plane.api.app import create_control_plane_app


def create_app() -> FastAPI:
    """Create the API application instance."""
    return create_control_plane_app()


app = create_app()
