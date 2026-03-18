"""Persistence helpers for CEO governance records."""

from __future__ import annotations

import json
from datetime import UTC, datetime

from openqilin.data_access.repositories.artifacts import ProjectArtifactWriteContext
from openqilin.data_access.repositories.postgres.governance_artifact_repository import (
    PostgresGovernanceArtifactRepository,
)

_CEO_PROPOSAL_WRITE_CONTEXT = ProjectArtifactWriteContext(
    actor_role="ceo",
    project_status="proposed",
)
_CEO_COAPPROVAL_WRITE_CONTEXT = ProjectArtifactWriteContext(
    actor_role="ceo",
    project_status="active",
)


class CeoDecisionWriter:
    """Persists CEO decision records and co-approval evidence."""

    def __init__(self, governance_repo: PostgresGovernanceArtifactRepository) -> None:
        self._governance_repo = governance_repo

    def write_proposal_decision(
        self,
        *,
        proposal_id: str,
        project_id: str | None,
        decision: str,
        rationale: str,
        cso_review_outcome: str | None,
        revision_cycle_count: int,
        override_flag: bool,
        trace_id: str,
    ) -> None:
        durable_project_id = _require_project_scope(project_id, proposal_id=proposal_id)
        self._governance_repo.write_project_artifact(
            project_id=durable_project_id,
            artifact_type="ceo_proposal_decision",
            content=json.dumps(
                {
                    "event_type": "ceo_proposal_decision",
                    "proposal_id": proposal_id,
                    "decision": decision,
                    "rationale": rationale,
                    "cso_review_outcome": cso_review_outcome,
                    "revision_cycle_count": revision_cycle_count,
                    "override_flag": override_flag,
                    "trace_id": trace_id,
                    "created_at": datetime.now(tz=UTC).isoformat(),
                }
            ),
            write_context=_CEO_PROPOSAL_WRITE_CONTEXT,
        )

    def write_coapproval_record(
        self,
        *,
        project_id: str,
        approval_type: str,
        artifact_type: str | None,
        trace_id: str,
    ) -> None:
        self._governance_repo.write_project_artifact(
            project_id=project_id,
            artifact_type="ceo_coapproval",
            content=json.dumps(
                {
                    "event_type": "ceo_coapproval",
                    "approval_type": approval_type,
                    "artifact_type": artifact_type,
                    "trace_id": trace_id,
                    "created_at": datetime.now(tz=UTC).isoformat(),
                }
            ),
            write_context=_CEO_COAPPROVAL_WRITE_CONTEXT,
        )


def _require_project_scope(project_id: str | None, *, proposal_id: str) -> str:
    # REVIEW_NOTE: the handoff allows ``project_id=None`` here, but the governed artifact
    # repository requires a durable project scope. Fail closed until the Architect specifies
    # proposal-only storage semantics for CEO gate records.
    if project_id is None or not project_id.strip():
        raise ValueError(f"CEO decision record requires project_id for proposal {proposal_id}")
    return project_id.strip()
