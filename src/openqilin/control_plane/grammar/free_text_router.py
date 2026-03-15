"""Grammar layer free-text router: resolve routing target from intent and chat context."""

from __future__ import annotations

from openqilin.control_plane.grammar.models import ChatContext, IntentClass, RoutingHint

_INSTITUTIONAL_CLASSES: frozenset[str] = frozenset(
    {"leadership_council", "governance", "executive"}
)

_SECRETARY_ROLE = "secretary"
_PROJECT_MANAGER_ROLE = "project_manager"


class FreeTextRouter:
    """Resolve routing target role from intent class and chat context.

    Routing priority per OwnerInteractionGrammar.md §6:
    1. Project channel → project_manager
    2. Institutional channel (leadership_council, governance, executive) → secretary
    3. Direct channel or fallback → secretary (default triage responder)
    """

    def resolve(self, intent: IntentClass, context: ChatContext) -> RoutingHint:
        """Resolve routing hint. MUTATION intent should not reach this method."""
        if context.chat_class == "project":
            return RoutingHint(
                target_role=_PROJECT_MANAGER_ROLE,
                project_id=context.project_id,
                confidence=0.9,
            )

        if context.chat_class in _INSTITUTIONAL_CLASSES:
            if intent in (IntentClass.DISCUSSION, IntentClass.QUERY):
                return RoutingHint(
                    target_role=_SECRETARY_ROLE,
                    project_id=context.project_id,
                    confidence=0.9,
                )

        # Direct channel or unresolved → secretary as default triage responder
        return RoutingHint(
            target_role=_SECRETARY_ROLE,
            project_id=context.project_id,
            confidence=0.7,
        )
