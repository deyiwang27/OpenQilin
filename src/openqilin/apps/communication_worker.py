"""Async entrypoint for the OpenQilin communication worker."""

import asyncio

import structlog

LOGGER = structlog.get_logger(__name__)


async def main() -> None:
    """Run one bootstrap cycle for the communication worker."""
    LOGGER.info("worker.bootstrap", worker="communication_worker")
    await asyncio.sleep(0)


if __name__ == "__main__":
    asyncio.run(main())
