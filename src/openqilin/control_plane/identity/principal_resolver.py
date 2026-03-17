"""Principal resolution utilities for governed ingress."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Mapping

if TYPE_CHECKING:
    from openqilin.data_access.repositories.identity_channels import (
        InMemoryIdentityChannelRepository,
    )
    from openqilin.data_access.repositories.postgres.identity_repository import (
        PostgresIdentityMappingRepository,
    )

    IdentityRepo = InMemoryIdentityChannelRepository | PostgresIdentityMappingRepository


class PrincipalResolutionError(ValueError):
    """Raised when inbound identity headers are missing or malformed."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True, slots=True)
class Principal:
    """Normalized principal identity for admission flow."""

    principal_id: str
    connector: str
    principal_role: str
    trust_domain: str


def _required_header(headers: Mapping[str, str], header_name: str) -> str:
    value = headers.get(header_name)
    if value is None:
        raise PrincipalResolutionError(
            code="principal_missing_header",
            message=f"missing required header: {header_name}",
        )

    normalized = value.strip()
    if not normalized:
        raise PrincipalResolutionError(
            code="principal_invalid_header",
            message=f"header has empty value: {header_name}",
        )
    return normalized


def _optional_header(headers: Mapping[str, str], header_name: str) -> str | None:
    value = headers.get(header_name)
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def resolve_principal(
    headers: Mapping[str, str],
    *,
    identity_repo: "IdentityRepo | None" = None,
) -> Principal:
    """Resolve principal identity from connector-originated HTTP headers.

    When *identity_repo* is provided (production path for external connectors):
    - The actor's identity must be verified in the DB.
    - The role comes from the DB record, not from any inbound header.

    When *identity_repo* is None (internal connectors or legacy admin paths):
    - Role falls back to the ``x-openqilin-actor-role`` header value, defaulting
      to ``"owner"``.  This path should only be used for trusted internal
      callers where role self-assertion is acceptable.
    """

    connector = _optional_header(headers, "x-external-channel") or _optional_header(
        headers, "x-openqilin-connector"
    )
    if connector is None:
        raise PrincipalResolutionError(
            code="principal_missing_header",
            message="missing required header: x-external-channel",
        )
    if connector not in {"discord", "internal"}:
        raise PrincipalResolutionError(
            code="principal_invalid_connector",
            message=f"unsupported connector: {connector}",
        )

    actor_external_id = (
        _optional_header(headers, "x-openqilin-actor-external-id")
        or _optional_header(headers, "x-external-actor-id")
        or _optional_header(headers, "x-openqilin-user-id")
    )
    if actor_external_id is None:
        raise PrincipalResolutionError(
            code="principal_missing_header",
            message=(
                "missing required header: x-openqilin-actor-external-id (or x-external-actor-id)"
            ),
        )

    # C-6 fix: for external connectors backed by a persistent (Postgres) identity store,
    # role must come from the DB record and the actor must be verified.
    # InMemory repos (dev/test) skip the verified gate — they never run in production
    # (governance constraint: no InMemory* in production paths).
    _is_persistent_identity_store = hasattr(identity_repo, "_session_factory")
    if identity_repo is not None and connector != "internal" and _is_persistent_identity_store:
        mapping = identity_repo.get_by_connector_actor(connector, actor_external_id)
        if mapping is None or mapping.status != "verified":
            raise PrincipalResolutionError(
                code="principal_identity_unverified",
                message="actor identity is not verified; access denied",
            )
        principal_role = mapping.principal_role or "owner"
    elif identity_repo is not None and connector != "internal":
        # InMemory repo (dev/test): use DB role if a verified mapping exists, else header role.
        mapping = identity_repo.get_by_connector_actor(connector, actor_external_id)
        principal_role = (
            mapping.principal_role or "owner"
            if mapping is not None
            else _optional_header(headers, "x-openqilin-actor-role") or "owner"
        )
    else:
        # Internal connector or legacy admin paths: role from header (trusted caller context).
        principal_role = _optional_header(headers, "x-openqilin-actor-role") or "owner"

    trust_domain = "internal" if connector == "internal" else "external_verified"
    principal_id = actor_external_id
    return Principal(
        principal_id=principal_id,
        connector=connector,
        principal_role=principal_role,
        trust_domain=trust_domain,
    )
