"""Channel availability constraints for advisory agent routing."""

from __future__ import annotations

CHANNEL_RESTRICTED_ROLES: frozenset[str] = frozenset({"auditor", "administrator"})


def is_role_available_in_channel(role: str, is_project_channel: bool) -> bool:
    """Return True if the role can respond in the given channel type.

    Auditor and Administrator are not available in project channels.
    All roles are available in general (non-project) channels.
    """
    if is_project_channel and role in CHANNEL_RESTRICTED_ROLES:
        return False
    return True
