"""Async entrypoint for the OpenQilin orchestrator worker."""

import asyncio

import structlog

LOGGER = structlog.get_logger(__name__)


async def main() -> None:
    """Run one bootstrap cycle for the orchestrator worker."""
    LOGGER.info("worker.bootstrap", worker="orchestrator_worker")
    await asyncio.sleep(0)


if __name__ == "__main__":
    asyncio.run(main())
