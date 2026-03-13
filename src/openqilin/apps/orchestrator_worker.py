"""Async entrypoint for the OpenQilin orchestrator worker."""

import asyncio
from pathlib import Path

import structlog

from openqilin.shared_kernel.config import RuntimeSettings
from openqilin.shared_kernel.startup_validation import enforce_connector_secret_hardening

LOGGER = structlog.get_logger(__name__)
READY_MARKER_PATH = Path("/tmp/openqilin.orchestrator_worker.ready")


def _mark_ready() -> None:
    """Emit deterministic ready marker for container health checks."""

    READY_MARKER_PATH.write_text("ready\n", encoding="utf-8")


async def main(*, run_once: bool = False) -> None:
    """Run orchestrator worker bootstrap and optional steady-state loop."""

    enforce_connector_secret_hardening(RuntimeSettings())
    LOGGER.info("worker.bootstrap", worker="orchestrator_worker")
    _mark_ready()
    if run_once:
        return

    while True:
        await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(main())
