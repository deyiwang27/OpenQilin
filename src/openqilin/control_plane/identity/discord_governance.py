"""Discord chat-governance and identity/channel baseline checks for ingress."""

from __future__ import annotations

from dataclasses import dataclass

from openqilin.control_plane.schemas.owner_commands import OwnerCommandRequest
from openqilin.data_access.repositories.governance import InMemoryGovernanceRepository
from openqilin.data_access.repositories.identity_channels import (
    IdentityChannelMappingRecord,
    InMemoryIdentityChannelRepository,
)

# secretary activated in M11; cso and domain_leader remain pending until M12/M13
_PENDING_ROLE_FLAGS = frozenset({"cso", "domain_leader"})
_MEMBERSHIP_BY_CHAT_CLASS: dict[str, frozenset[str]] = {
    "direct": frozenset(
        {"owner", "administrator", "auditor", "ceo", "cwo", "cso", "secretary", "project_manager"}
    ),
    "leadership_council": frozenset(
        {"owner", "administrator", "auditor", "ceo", "cwo", "secretary"}
    ),
    "governance": frozenset({"owner", "administrator", "auditor", "secretary"}),
    "executive": frozenset({"owner", "ceo", "cwo", "secretary"}),
    "project": frozenset({"owner", "ceo", "cwo", "project_manager"}),
}
_KNOWN_ROLE_SET = frozenset(
    {
        "owner",
        "administrator",
        "auditor",
        "ceo",
        "cwo",
        "project_manager",
        "domain_leader",
        "specialist",
        "secretary",
        "cso",
    }
)


@dataclass(frozen=True, slots=True)
class DiscordGovernanceDecision:
    """Result from Discord governance validation."""

    mapping: IdentityChannelMappingRecord
    chat_class: str
    project_status: str | None


class DiscordGovernanceError(ValueError):
    """Raised when Discord governance checks must deny ingress."""

    def __init__(self, code: str, message: str, *, details: dict[str, str] | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}


def validate_discord_governance(
    *,
    payload: OwnerCommandRequest,
    principal_role: str,
    identity_channel_repository: InMemoryIdentityChannelRepository,
    governance_repository: InMemoryGovernanceRepository,
) -> DiscordGovernanceDecision | None:
    """Validate Discord ingress context, identity/channel mapping, and chat governance."""

    if payload.connector.channel != "discord":
        return None

    context = payload.connector.discord_context
    if context is None:
        raise DiscordGovernanceError(
            code="connector_discord_context_missing",
            message="discord connector requires context metadata",
        )

    mapping = identity_channel_repository.claim_mapping(
        connector=payload.connector.channel,
        actor_external_id=payload.connector.actor_external_id,
        guild_id=context.guild_id,
        channel_id=context.channel_id,
        channel_type=context.channel_type,
    )
    if mapping.status == "revoked":
        raise DiscordGovernanceError(
            code="connector_identity_channel_revoked",
            message="connector actor/channel mapping is revoked",
            details={
                "guild_id": context.guild_id,
                "channel_id": context.channel_id,
                "channel_type": context.channel_type,
            },
        )

    chat_class = context.chat_class
    allowed_members = _MEMBERSHIP_BY_CHAT_CLASS.get(chat_class)
    if allowed_members is None:
        raise DiscordGovernanceError(
            code="governance_chat_class_unknown",
            message=f"unknown chat_class: {chat_class!r}",
            details={"chat_class": chat_class},
        )
    normalized_principal_role = principal_role.strip().lower()
    if normalized_principal_role not in allowed_members:
        raise DiscordGovernanceError(
            code="governance_chat_sender_forbidden",
            message=f"sender role is not allowed for chat_class {chat_class}",
            details={"chat_class": chat_class, "sender_role": normalized_principal_role},
        )

    recipient_roles = tuple(
        recipient.recipient_type.strip().lower() for recipient in payload.recipients
    )
    for recipient_role in recipient_roles:
        if recipient_role == "specialist":
            # Specialist direct-touchability is enforced by governed policy evaluation path.
            continue
        if recipient_role in _PENDING_ROLE_FLAGS:
            raise DiscordGovernanceError(
                code="governance_chat_role_pending_activation",
                message=f"recipient role is pending activation in MVP: {recipient_role}",
                details={"chat_class": chat_class, "recipient_role": recipient_role},
            )
        if recipient_role in _KNOWN_ROLE_SET and recipient_role not in allowed_members:
            raise DiscordGovernanceError(
                code="governance_chat_recipient_forbidden",
                message=f"recipient role is not allowed for chat_class {chat_class}",
                details={"chat_class": chat_class, "recipient_role": recipient_role},
            )

    if chat_class != "project":
        return DiscordGovernanceDecision(
            mapping=mapping, chat_class=chat_class, project_status=None
        )

    if payload.project_id is None:
        raise DiscordGovernanceError(
            code="governance_project_channel_missing_project_id",
            message="project chat class requires project_id",
            details={"chat_class": chat_class},
        )
    project = governance_repository.get_project(payload.project_id)
    if project is None:
        return DiscordGovernanceDecision(
            mapping=mapping, chat_class=chat_class, project_status=None
        )

    project_status = project.status
    if project_status == "archived":
        raise DiscordGovernanceError(
            code="governance_project_channel_archived",
            message="project channel is archived and locked",
            details={"project_id": payload.project_id, "project_status": project_status},
        )
    if project_status in {"completed", "terminated"} and not payload.command.action.startswith(
        "query_"
    ):
        raise DiscordGovernanceError(
            code="governance_project_channel_read_only",
            message="project channel is read-only in completed/terminated state",
            details={"project_id": payload.project_id, "project_status": project_status},
        )

    allowed_senders = (
        frozenset({"owner", "ceo", "cwo"})
        if project_status == "proposed"
        else frozenset({"owner", "ceo", "cwo", "project_manager"})
    )
    if normalized_principal_role not in allowed_senders:
        raise DiscordGovernanceError(
            code="governance_project_channel_sender_forbidden",
            message="sender role is not allowed for project status",
            details={
                "project_id": payload.project_id,
                "project_status": project_status,
                "sender_role": normalized_principal_role,
            },
        )
    return DiscordGovernanceDecision(
        mapping=mapping,
        chat_class=chat_class,
        project_status=project_status,
    )
