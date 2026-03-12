from openqilin.release_readiness.artifact_packaging import (
    ReleaseArtifactBundle,
    build_release_artifact_bundle,
    render_release_promotion_checklist_markdown,
    serialize_release_artifact_bundle,
    validate_release_artifact_bundle,
)


def test_release_artifact_bundle_contains_required_contract_entries() -> None:
    bundle = build_release_artifact_bundle(
        release_version="0.1.0-rc1",
        git_commit="abc1234",
        generated_at_utc="2026-03-12T00:00:00+00:00",
    )

    assert bundle.bundle_schema_version == "v1"
    assert len(bundle.artifacts) >= 8
    assert len(bundle.decision_points) == 4
    assert bundle.artifact_index_ref.endswith("ReleaseArtifactIndex-v1.md")
    assert bundle.promotion_checklist_ref.endswith("ReleasePromotionChecklist-v1.md")


def test_release_artifact_bundle_validation_fails_without_rollback_hooks() -> None:
    bundle = build_release_artifact_bundle(
        release_version="0.1.0-rc1",
        git_commit="abc1234",
        generated_at_utc="2026-03-12T00:00:00+00:00",
    )
    broken = ReleaseArtifactBundle(
        bundle_schema_version=bundle.bundle_schema_version,
        release_version=bundle.release_version,
        git_commit=bundle.git_commit,
        generated_at_utc=bundle.generated_at_utc,
        artifacts=bundle.artifacts,
        decision_points=(
            *bundle.decision_points[:-1],
            type(bundle.decision_points[-1])(
                decision_id=bundle.decision_points[-1].decision_id,
                owner_role=bundle.decision_points[-1].owner_role,
                decision_prompt=bundle.decision_points[-1].decision_prompt,
                pass_criteria=bundle.decision_points[-1].pass_criteria,
                fail_action=bundle.decision_points[-1].fail_action,
                rollback_hook="manual escalation only",
            ),
        ),
        artifact_index_ref=bundle.artifact_index_ref,
        promotion_checklist_ref=bundle.promotion_checklist_ref,
    )

    failures = validate_release_artifact_bundle(broken)
    assert any("rollback_hook must mention rollback behavior" in failure for failure in failures)


def test_rendered_release_checklist_contains_decision_points_and_rollback_hooks() -> None:
    bundle = build_release_artifact_bundle(
        release_version="0.1.0-rc1",
        git_commit="abc1234",
        generated_at_utc="2026-03-12T00:00:00+00:00",
    )

    rendered = render_release_promotion_checklist_markdown(bundle)
    assert "D1_ci_and_quality_gates" in rendered
    assert "D4_manual_go_no_go" in rendered
    assert "Rollback hook" in rendered

    serialized = serialize_release_artifact_bundle(bundle)
    assert serialized["release_version"] == "0.1.0-rc1"
    assert serialized["git_commit"] == "abc1234"
