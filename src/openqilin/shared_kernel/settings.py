"""RuntimeSettings singleton factory.

Production code must call ``get_settings()`` — never construct ``RuntimeSettings()``
directly. Test fixtures may call ``get_settings.cache_clear()`` to reset the cache
between test cases.
"""

from functools import lru_cache

from openqilin.shared_kernel.config import RuntimeSettings


@lru_cache(maxsize=1)
def get_settings() -> RuntimeSettings:
    """Return the process-wide RuntimeSettings singleton.

    Reads environment variables exactly once on first call.
    Subsequent calls return the cached instance — zero I/O.
    """
    return RuntimeSettings()
