"""Grammar layer free-text router: resolve routing target from intent and chat context."""

from __future__ import annotations

from openqilin.control_plane.grammar.models import ChatContext, IntentClass, RoutingHint

_INSTITUTIONAL_CLASSES: frozenset[str] = frozenset(
    {"leadership_council", "governance", "executive"}
)

# Channels where CSO reviews governed actions (MUTATION/ADMIN intents).
_CSO_ROUTING_CLASSES: frozenset[str] = frozenset({"leadership_council", "executive"})

_SECRETARY_ROLE = "secretary"
_PROJECT_MANAGER_ROLE = "project_manager"
_CSO_ROLE = "cso"

# Intent classes that require CSO review in governed institutional channels.
_GOVERNED_INTENTS: frozenset[IntentClass] = frozenset({IntentClass.MUTATION, IntentClass.ADMIN})


class FreeTextRouter:
    """Resolve routing target role from intent class and chat context.

    Routing priority per OwnerInteractionGrammar.md §6 and M13-WP8:
    1. Project channel → project_manager
    2. Institutional channel (executive/leadership_council) + MUTATION/ADMIN → cso
    3. Institutional channel + DISCUSSION/QUERY → secretary
    4. Direct channel or fallback → secretary (default triage responder)
    """

    def resolve(self, intent: IntentClass, context: ChatContext) -> RoutingHint:
        """Resolve routing hint from intent class and channel context."""
        if context.chat_class == "project":
            return RoutingHint(
                target_role=_PROJECT_MANAGER_ROLE,
                project_id=context.project_id,
                confidence=0.9,
            )

        if context.chat_class in _INSTITUTIONAL_CLASSES:
            if context.chat_class in _CSO_ROUTING_CLASSES and intent in _GOVERNED_INTENTS:
                # MUTATION/ADMIN in executive/leadership_council → CSO reviews governed actions
                return RoutingHint(
                    target_role=_CSO_ROLE,
                    project_id=context.project_id,
                    confidence=0.9,
                )
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
