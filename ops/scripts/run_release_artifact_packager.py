"""Build release artifact package outputs for operator handoff."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from openqilin.release_readiness.artifact_packaging import (
    build_release_artifact_bundle,
    render_release_promotion_checklist_markdown,
    serialize_release_artifact_bundle,
    validate_release_artifact_bundle,
)


def _resolve_repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _default_git_commit() -> str:
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
    except Exception:
        return "unknown"
    return completed.stdout.strip() or "unknown"


def _build_parser() -> argparse.ArgumentParser:
    repo_root = _resolve_repo_root()
    parser = argparse.ArgumentParser(
        description="Generate OpenQilin release artifact package and checklist outputs."
    )
    parser.add_argument(
        "--release-version",
        default="0.1.0-rc-template",
        help="Release candidate version identifier.",
    )
    parser.add_argument(
        "--git-commit",
        default=_default_git_commit(),
        help="Git commit hash to pin in artifact package.",
    )
    parser.add_argument(
        "--bundle-output",
        type=Path,
        default=repo_root
        / "implementation/v1/planning/artifacts/release_candidate_bundle_latest.json",
        help="Destination JSON path for release artifact bundle.",
    )
    parser.add_argument(
        "--checklist-output",
        type=Path,
        default=repo_root
        / "implementation/v1/planning/artifacts/release_promotion_checklist_latest.md",
        help="Destination markdown path for rendered promotion checklist.",
    )
    return parser


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    bundle = build_release_artifact_bundle(
        release_version=args.release_version,
        git_commit=args.git_commit,
    )
    failures = validate_release_artifact_bundle(bundle)
    if failures:
        print("Release artifact bundle validation failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1

    serialized = serialize_release_artifact_bundle(bundle)
    checklist_markdown = render_release_promotion_checklist_markdown(bundle)

    args.bundle_output.parent.mkdir(parents=True, exist_ok=True)
    args.bundle_output.write_text(
        json.dumps(serialized, indent=2, sort_keys=True), encoding="utf-8"
    )
    args.checklist_output.parent.mkdir(parents=True, exist_ok=True)
    args.checklist_output.write_text(checklist_markdown, encoding="utf-8")

    print(f"[OK] bundle: {args.bundle_output}")
    print(f"[OK] checklist: {args.checklist_output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
