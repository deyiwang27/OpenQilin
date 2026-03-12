"""Static checks for release artifact package docs and bundle contract."""

from __future__ import annotations

import sys
from pathlib import Path

from openqilin.release_readiness.artifact_packaging import (
    build_release_artifact_bundle,
    render_release_promotion_checklist_markdown,
    validate_release_artifact_bundle,
)


def _load_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def main() -> int:
    repo_root = Path(__file__).resolve().parents[2]
    failures: list[str] = []

    bundle = build_release_artifact_bundle(
        release_version="0.1.0-rc-template",
        git_commit="deadbee",
        generated_at_utc="2026-03-12T00:00:00+00:00",
    )
    failures.extend(validate_release_artifact_bundle(bundle))

    rendered = render_release_promotion_checklist_markdown(bundle)
    for snippet in ("Decision Points", "Rollback hook", "D1_ci_and_quality_gates"):
        if snippet not in rendered:
            failures.append(
                f"rendered promotion checklist markdown missing required snippet: {snippet!r}"
            )

    promotion_checklist = repo_root / "implementation/v1/quality/ReleasePromotionChecklist-v1.md"
    artifact_index = repo_root / "implementation/v1/planning/ReleaseArtifactIndex-v1.md"
    m4_evidence_pack = repo_root / "implementation/v1/planning/M4EvidencePack-v1.md"
    for path in (promotion_checklist, artifact_index, m4_evidence_pack):
        if not path.exists():
            failures.append(f"required M4 document missing: {path.relative_to(repo_root)}")

    if promotion_checklist.exists():
        checklist_text = _load_text(promotion_checklist)
        for snippet in (
            "D1_ci_and_quality_gates",
            "D2_release_candidate_gate_matrix",
            "D3_migration_and_rollback_readiness",
            "D4_manual_go_no_go",
            "Rollback Hook",
        ):
            if snippet not in checklist_text:
                failures.append(
                    "ReleasePromotionChecklist-v1.md missing decision/rollback snippet: "
                    f"{snippet!r}"
                )

    if artifact_index.exists():
        artifact_text = _load_text(artifact_index)
        for snippet in (
            "compose.yml",
            "implementation/v1/quality/ReleasePromotionChecklist-v1.md",
            "src/openqilin/release_readiness/gate_matrix.py",
        ):
            if snippet not in artifact_text:
                failures.append(
                    f"ReleaseArtifactIndex-v1.md missing required artifact reference: {snippet!r}"
                )

    if failures:
        print("Release artifact package checks failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("Release artifact package checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
