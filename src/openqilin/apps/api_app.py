"""FastAPI entrypoint for the OpenQilin control-plane API.

Usage with uvicorn:
    uvicorn openqilin.apps.api_app:app

The module-level ``app`` is built lazily the first time it is accessed.
This avoids triggering ``build_runtime_services()`` at import time for
unit tests and CLI tools that import only ``create_app``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import FastAPI

from openqilin.control_plane.api.app import create_control_plane_app

if TYPE_CHECKING:
    # Expose ``app`` as a FastAPI instance for type checkers (mypy) even though
    # it is produced lazily at runtime via ``__getattr__``.
    app: FastAPI

_app: FastAPI | None = None


def create_app() -> FastAPI:
    """Create the API application instance."""
    return create_control_plane_app()


def __getattr__(name: str) -> object:
    global _app
    if name == "app":
        if _app is None:
            _app = create_app()
        return _app
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
