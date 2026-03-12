"""Release artifact packaging contracts for promotion handoff."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Any


@dataclass(frozen=True, slots=True)
class ReleaseArtifactItem:
    """One required release artifact with traceability metadata."""

    artifact_id: str
    description: str
    source_path: str
    evidence_ref: str
    required: bool = True


@dataclass(frozen=True, slots=True)
class PromotionDecisionPoint:
    """Promotion decision point with explicit rollback hook."""

    decision_id: str
    owner_role: str
    decision_prompt: str
    pass_criteria: str
    fail_action: str
    rollback_hook: str


@dataclass(frozen=True, slots=True)
class ReleaseArtifactBundle:
    """Release-candidate artifact package contract."""

    bundle_schema_version: str
    release_version: str
    git_commit: str
    generated_at_utc: str
    artifacts: tuple[ReleaseArtifactItem, ...]
    decision_points: tuple[PromotionDecisionPoint, ...]
    artifact_index_ref: str
    promotion_checklist_ref: str


def build_release_artifact_index_items() -> tuple[ReleaseArtifactItem, ...]:
    """Build required release artifact index entries."""

    return (
        ReleaseArtifactItem(
            artifact_id="compose_full_profile",
            description="Full-profile runtime topology and dependency startup order.",
            source_path="compose.yml",
            evidence_ref="M2-WP4 pgvector + M4-WP3 smoke gate alignment",
        ),
        ReleaseArtifactItem(
            artifact_id="dependency_lock",
            description="Reproducible dependency lock for release candidate.",
            source_path="uv.lock",
            evidence_ref="CI frozen sync contract",
        ),
        ReleaseArtifactItem(
            artifact_id="migration_contract",
            description="Schema and pgvector baseline migration contract.",
            source_path="migrations/versions/20260311_0001_pgvector_baseline_contract.py",
            evidence_ref="M2-WP4 migration baseline",
        ),
        ReleaseArtifactItem(
            artifact_id="rollback_drill_contract",
            description="Rollback drill modes and evidence output contract.",
            source_path="implementation/v1/quality/ReleaseVersioningAndRollback-v1.md",
            evidence_ref="M4-WP2",
        ),
        ReleaseArtifactItem(
            artifact_id="release_gate_matrix_contract",
            description="Deterministic CI/release-candidate gate matrix contract.",
            source_path="src/openqilin/release_readiness/gate_matrix.py",
            evidence_ref="M4-WP3",
        ),
        ReleaseArtifactItem(
            artifact_id="observability_alert_contract",
            description="Release-readiness dashboard and alert threshold baseline.",
            source_path="src/openqilin/observability/alerts/release_readiness.py",
            evidence_ref="M4-WP1",
        ),
        ReleaseArtifactItem(
            artifact_id="artifact_index",
            description="Operator-facing artifact index with traceability links.",
            source_path="implementation/v1/planning/ReleaseArtifactIndex-v1.md",
            evidence_ref="M4-WP4",
        ),
        ReleaseArtifactItem(
            artifact_id="promotion_checklist",
            description="Operator-facing promotion and rollback decision checklist.",
            source_path="implementation/v1/quality/ReleasePromotionChecklist-v1.md",
            evidence_ref="M4-WP4",
        ),
    )


def build_promotion_decision_points() -> tuple[PromotionDecisionPoint, ...]:
    """Build explicit promotion/rollback decision points."""

    return (
        PromotionDecisionPoint(
            decision_id="D1_ci_and_quality_gates",
            owner_role="administrator",
            decision_prompt="Are CI and mandatory quality gates green on the release candidate commit?",
            pass_criteria="All CI jobs pass, including release-gate/migration/spec integrity checks.",
            fail_action="Block promotion and remediate failing gate before retry.",
            rollback_hook=(
                "No rollback execution required; keep current production version unchanged "
                "because promotion is blocked."
            ),
        ),
        PromotionDecisionPoint(
            decision_id="D2_release_candidate_gate_matrix",
            owner_role="auditor",
            decision_prompt=(
                "Do release-candidate gate matrix outputs confirm smoke + conformance readiness?"
            ),
            pass_criteria=(
                "release-candidate matrix command sequence is complete with no failed steps."
            ),
            fail_action="Declare release candidate non-promotable and open remediation work item.",
            rollback_hook=(
                "If deployment already started, execute application rollback to last compatible version."
            ),
        ),
        PromotionDecisionPoint(
            decision_id="D3_migration_and_rollback_readiness",
            owner_role="owner",
            decision_prompt=(
                "Are migration forward-apply and rollback drill records complete for this release?"
            ),
            pass_criteria=(
                "Migration contract checks pass and rollback drill evidence contains operator/reason/version."
            ),
            fail_action="Block promotion until migration/rollback evidence is complete and validated.",
            rollback_hook=(
                "Execute restore-mode rollback using recorded backup/snapshot reference."
            ),
        ),
        PromotionDecisionPoint(
            decision_id="D4_manual_go_no_go",
            owner_role="ceo",
            decision_prompt="Final go/no-go: should this release candidate be promoted?",
            pass_criteria="Owner, auditor, and administrator approvals are explicitly recorded.",
            fail_action="Reject release candidate and retain current production baseline.",
            rollback_hook=(
                "If post-promotion incidents occur, trigger incident rollback protocol and record audit metadata."
            ),
        ),
    )


def build_release_artifact_bundle(
    *,
    release_version: str,
    git_commit: str,
    generated_at_utc: str | None = None,
) -> ReleaseArtifactBundle:
    """Build release-candidate package metadata."""

    timestamp = generated_at_utc or datetime.now(tz=UTC).isoformat()
    return ReleaseArtifactBundle(
        bundle_schema_version="v1",
        release_version=release_version,
        git_commit=git_commit,
        generated_at_utc=timestamp,
        artifacts=build_release_artifact_index_items(),
        decision_points=build_promotion_decision_points(),
        artifact_index_ref="implementation/v1/planning/ReleaseArtifactIndex-v1.md",
        promotion_checklist_ref="implementation/v1/quality/ReleasePromotionChecklist-v1.md",
    )


def serialize_release_artifact_bundle(bundle: ReleaseArtifactBundle) -> dict[str, Any]:
    """Serialize release artifact bundle into JSON-safe mapping."""

    return asdict(bundle)


def render_release_promotion_checklist_markdown(bundle: ReleaseArtifactBundle) -> str:
    """Render operator checklist markdown from bundle decision points."""

    lines = [
        f"# Release Candidate Promotion Checklist ({bundle.release_version})",
        "",
        f"- Git commit: `{bundle.git_commit}`",
        f"- Generated at UTC: `{bundle.generated_at_utc}`",
        f"- Artifact index: `{bundle.artifact_index_ref}`",
        "",
        "## Decision Points",
    ]
    for decision in bundle.decision_points:
        lines.extend(
            [
                f"### {decision.decision_id}",
                f"- Owner role: `{decision.owner_role}`",
                f"- Decision: {decision.decision_prompt}",
                f"- Pass criteria: {decision.pass_criteria}",
                f"- Fail action: {decision.fail_action}",
                f"- Rollback hook: {decision.rollback_hook}",
                "",
            ]
        )
    lines.extend(["## Required Artifacts", ""])
    for artifact in bundle.artifacts:
        required_label = "required" if artifact.required else "optional"
        lines.append(
            f"- `{artifact.artifact_id}` ({required_label}): `{artifact.source_path}`"
            f" - {artifact.description} (evidence: {artifact.evidence_ref})"
        )
    lines.append("")
    return "\n".join(lines)


def validate_release_artifact_bundle(bundle: ReleaseArtifactBundle) -> list[str]:
    """Validate release artifact package completeness."""

    failures: list[str] = []

    if not bundle.release_version.strip():
        failures.append("release_version must be non-empty")
    if not bundle.git_commit.strip():
        failures.append("git_commit must be non-empty")
    if not bundle.artifacts:
        failures.append("artifact list must be non-empty")
    if not bundle.decision_points:
        failures.append("decision_points must be non-empty")

    artifact_ids = [artifact.artifact_id for artifact in bundle.artifacts]
    duplicate_artifact_ids = sorted(
        {artifact_id for artifact_id in artifact_ids if artifact_ids.count(artifact_id) > 1}
    )
    if duplicate_artifact_ids:
        failures.append(f"duplicate artifact_id values: {', '.join(duplicate_artifact_ids)}")

    decision_ids = [decision.decision_id for decision in bundle.decision_points]
    duplicate_decision_ids = sorted(
        {decision_id for decision_id in decision_ids if decision_ids.count(decision_id) > 1}
    )
    if duplicate_decision_ids:
        failures.append(f"duplicate decision_id values: {', '.join(duplicate_decision_ids)}")

    for artifact in bundle.artifacts:
        if not artifact.source_path.strip():
            failures.append(f"{artifact.artifact_id}: source_path must be non-empty")
        if not artifact.evidence_ref.strip():
            failures.append(f"{artifact.artifact_id}: evidence_ref must be non-empty")

    for decision in bundle.decision_points:
        if "rollback" not in decision.rollback_hook.lower():
            failures.append(f"{decision.decision_id}: rollback_hook must mention rollback behavior")
        if not decision.fail_action.strip():
            failures.append(f"{decision.decision_id}: fail_action must be non-empty")

    return failures
