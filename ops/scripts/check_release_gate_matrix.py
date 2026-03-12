"""Static checks for release-gate matrix and workflow alignment."""

from __future__ import annotations

import sys
from pathlib import Path

from openqilin.release_readiness.gate_matrix import ci_gate_steps, validate_release_gate_matrix


def _load_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def main() -> int:
    repo_root = Path(__file__).resolve().parents[2]
    failures = validate_release_gate_matrix()

    ci_workflow = repo_root / ".github/workflows/ci.yml"
    ci_text = _load_text(ci_workflow)
    for step in ci_gate_steps():
        if step.command not in ci_text:
            failures.append(
                f".github/workflows/ci.yml missing CI gate command from matrix: {step.command!r}"
            )

    compose_file = repo_root / "compose.yml"
    compose_text = _load_text(compose_file)
    if 'command: ["bootstrap", "--smoke-in-process"]' not in compose_text:
        failures.append(
            "compose.yml must pin admin full-profile command to bootstrap --smoke-in-process."
        )
    if 'profiles: ["full"]' not in compose_text:
        failures.append("compose.yml must contain full profile entries for release smoke workflow.")

    quality_doc = repo_root / "implementation/v1/quality/QualityAndDelivery-v1.md"
    quality_doc_text = _load_text(quality_doc)
    if "run_release_gate_matrix.py" not in quality_doc_text:
        failures.append(
            "implementation/v1/quality/QualityAndDelivery-v1.md must reference run_release_gate_matrix.py."
        )

    if failures:
        print("Release-gate matrix checks failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("Release-gate matrix checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
