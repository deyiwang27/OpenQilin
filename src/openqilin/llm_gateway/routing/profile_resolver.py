"""Routing profile resolver for llm gateway."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from openqilin.llm_gateway.schemas.requests import LlmModelClass


@dataclass(frozen=True, slots=True)
class RoutingProfile:
    """Resolved routing profile used by gateway."""

    profile_id: str
    status: str
    model_class_map: Mapping[LlmModelClass, tuple[str, ...]]
    max_fallback_hops: int


class RoutingProfileError(ValueError):
    """Raised when routing profile cannot be resolved."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


_ROUTING_PROFILES: dict[str, RoutingProfile] = {
    "dev_gemini_free": RoutingProfile(
        profile_id="dev_gemini_free",
        status="active",
        model_class_map={
            "interactive_fast": (
                "google_gemini_free_primary",
                "google_gemini_free_fallback",
            ),
            "reasoning_general": (
                "google_gemini_free_primary",
                "google_gemini_free_fallback",
            ),
            "embedding_text": ("google_gemini_free_primary",),
        },
        max_fallback_hops=1,
    ),
    "dev_deepseek": RoutingProfile(
        profile_id="dev_deepseek",
        status="active",
        model_class_map={
            "interactive_fast": (
                "deepseek_chat_primary",
                "deepseek_chat_fallback",
            ),
            "reasoning_general": (
                "deepseek_chat_primary",
                "deepseek_chat_fallback",
            ),
            "embedding_text": ("deepseek_chat_primary",),
        },
        max_fallback_hops=1,
    ),
    "prod_controlled": RoutingProfile(
        profile_id="prod_controlled",
        status="active",
        model_class_map={
            "interactive_fast": ("google_gemini_controlled_primary",),
            "reasoning_general": ("google_gemini_controlled_primary",),
            "embedding_text": ("google_gemini_controlled_primary",),
        },
        max_fallback_hops=1,
    ),
}


def resolve_routing_profile(profile_id: str) -> RoutingProfile:
    """Resolve active routing profile by identifier."""

    profile = _ROUTING_PROFILES.get(profile_id)
    if profile is None:
        raise RoutingProfileError(
            code="llm_unknown_routing_profile",
            message=f"unknown routing profile: {profile_id}",
        )
    if profile.status != "active":
        raise RoutingProfileError(
            code="llm_inactive_routing_profile",
            message=f"inactive routing profile: {profile_id}",
        )
    return profile
