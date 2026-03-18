"""Workforce initialization service for the CWO agent."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

import structlog

from openqilin.agents.cwo.models import CwoApprovalChainError
from openqilin.data_access.repositories.artifacts import (
    ProjectArtifactDocument,
    ProjectArtifactWriteContext,
)
from openqilin.data_access.repositories.postgres.agent_registry_repository import (
    PostgresAgentRegistryRepository,
)
from openqilin.data_access.repositories.postgres.governance_artifact_repository import (
    PostgresGovernanceArtifactRepository,
)

LOGGER = structlog.get_logger(__name__)

_CWO_APPROVED_WRITE_CONTEXT = ProjectArtifactWriteContext(
    actor_role="cwo",
    project_status="approved",
)


class WorkforceInitializer:
    """Binds workforce package metadata to a project after gate approval."""

    def __init__(
        self,
        governance_repo: PostgresGovernanceArtifactRepository,
        agent_registry_repo: PostgresAgentRegistryRepository,
    ) -> None:
        self._governance_repo = governance_repo
        self._agent_registry_repo = agent_registry_repo

    def initialize(
        self,
        project_id: str,
        template: str,
        llm_profile: str,
        system_prompt_package: str,
        trace_id: str,
    ) -> None:
        self._verify_approval_chain(project_id)
        self._governance_repo.write_project_artifact(
            project_id=project_id,
            artifact_type="workforce_plan",
            content=json.dumps(
                {
                    "artifact_type": "workforce_plan",
                    "author_role": "cwo",
                    "project_id": project_id,
                    "template": template,
                    "llm_profile": llm_profile,
                    "system_prompt_package": system_prompt_package,
                    "trace_id": trace_id,
                    "created_at": datetime.now(tz=UTC).isoformat(),
                },
                sort_keys=True,
            ),
            write_context=_CWO_APPROVED_WRITE_CONTEXT,
        )
        self._agent_registry_repo.bind_project_workforce(
            project_id=project_id,
            template=template,
            llm_profile=llm_profile,
            system_prompt_package=system_prompt_package,
        )
        if self._project_charter_absent(project_id):
            self._governance_repo.write_project_artifact(
                project_id=project_id,
                artifact_type="project_charter",
                content=json.dumps(
                    {
                        "artifact_type": "project_charter",
                        "author_role": "cwo",
                        "project_id": project_id,
                        "template": template,
                        "llm_profile": llm_profile,
                        "system_prompt_package": system_prompt_package,
                        "trace_id": trace_id,
                        "created_at": datetime.now(tz=UTC).isoformat(),
                    },
                    sort_keys=True,
                ),
                write_context=_CWO_APPROVED_WRITE_CONTEXT,
            )

    def _verify_approval_chain(self, project_id: str) -> None:
        missing: list[str] = []
        if not self._has_cso_review(project_id):
            missing.append("cso_review_outcome")
        if not self._has_ceo_approval(project_id):
            missing.append("ceo_proposal_decision=approved")
        if missing:
            raise CwoApprovalChainError(
                "Workforce initialization denied: missing approval evidence: " + ", ".join(missing)
            )
        if not self._has_owner_coapproval(project_id):
            LOGGER.info(
                "cwo.owner_coapproval_proxy_used",
                project_id=project_id,
            )

    def _has_cso_review(self, project_id: str) -> bool:
        for document in self._list_documents(project_id, "cso_review"):
            payload = _load_record_payload(document)
            event_type = _optional_str(payload.get("event_type"))
            if event_type in {None, "cso_review_outcome"}:
                return True
        return False

    def _has_ceo_approval(self, project_id: str) -> bool:
        for document in self._list_documents(project_id, "ceo_proposal_decision"):
            payload = _load_record_payload(document)
            if payload.get("decision") == "approved":
                return True
        return False

    def _has_owner_coapproval(self, project_id: str) -> bool:
        for document in self._list_documents(project_id, "decision_log"):
            payload = _load_record_payload(document)
            if _optional_str(payload.get("event_type")) == "owner_coapproval":
                return True
        return False

    def _project_charter_absent(self, project_id: str) -> bool:
        if hasattr(self._governance_repo, "read_latest_artifact"):
            document = self._governance_repo.read_latest_artifact(
                project_id=project_id,
                artifact_type="project_charter",
            )
            if document is not None:
                return False
        if hasattr(self._governance_repo, "_session_factory") and hasattr(
            self._governance_repo, "get_latest_pointer"
        ):
            pointer = self._governance_repo.get_latest_pointer(
                project_id=project_id,
                artifact_type="project_charter",
            )
            return pointer is None
        return True

    def _list_documents(
        self,
        project_id: str,
        artifact_type: str,
    ) -> tuple[ProjectArtifactDocument, ...]:
        return self._governance_repo.list_artifact_documents(
            project_id=project_id,
            artifact_type=artifact_type,
        )


def _load_record_payload(document: ProjectArtifactDocument) -> dict[str, Any]:
    try:
        raw = json.loads(document.content)
    except json.JSONDecodeError:
        return {}
    if isinstance(raw, dict):
        return raw
    return {}


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
