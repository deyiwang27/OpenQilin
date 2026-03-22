"""Async entrypoint for the OpenQilin communication worker."""

import asyncio
from pathlib import Path

import structlog

from openqilin.shared_kernel.settings import get_settings
from openqilin.shared_kernel.startup_validation import enforce_connector_secret_hardening

LOGGER = structlog.get_logger(__name__)
READY_MARKER_PATH = Path("/tmp/openqilin.communication_worker.ready")


def _mark_ready() -> None:
    """Emit deterministic ready marker for container health checks."""

    READY_MARKER_PATH.write_text("ready\n", encoding="utf-8")


async def main(*, run_once: bool = False) -> None:
    """Run communication worker bootstrap and optional steady-state loop."""

    enforce_connector_secret_hardening(get_settings())
    LOGGER.info("worker.bootstrap", worker="communication_worker")
    _mark_ready()
    if run_once:
        return

    while True:
        await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(main())
