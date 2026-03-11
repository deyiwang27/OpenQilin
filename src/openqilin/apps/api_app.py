"""FastAPI entrypoint for the OpenQilin control-plane API."""

from fastapi import FastAPI


def create_app() -> FastAPI:
    """Create the API application instance."""
    return FastAPI(title="OpenQilin API", version="0.1.0")


app = create_app()
