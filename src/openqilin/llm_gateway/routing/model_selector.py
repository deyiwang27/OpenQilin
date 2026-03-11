"""Model selection helpers for llm gateway routing."""

from __future__ import annotations

from openqilin.llm_gateway.routing.profile_resolver import RoutingProfile, RoutingProfileError
from openqilin.llm_gateway.schemas.requests import LlmModelClass


def select_model_aliases(profile: RoutingProfile, model_class: LlmModelClass) -> tuple[str, ...]:
    """Select ordered aliases for model class from resolved profile."""

    aliases = profile.model_class_map.get(model_class)
    if aliases is None or len(aliases) == 0:
        raise RoutingProfileError(
            code="llm_model_class_unmapped",
            message=f"model class not mapped in profile: {model_class}",
        )
    return aliases
