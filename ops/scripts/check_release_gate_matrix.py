"""Static checks for release-gate matrix and workflow alignment."""

from __future__ import annotations

import re
import sys
from pathlib import Path

from openqilin.release_readiness.gate_matrix import ci_gate_steps, validate_release_gate_matrix


def _load_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _extract_run_commands(ci_workflow_text: str) -> set[str]:
    pattern = re.compile(r"^\s*run:\s*(?P<command>\S.+?)\s*$", re.MULTILINE)
    return {match.group("command").strip() for match in pattern.finditer(ci_workflow_text)}


def _extract_compose_service_block(compose_text: str, service_name: str) -> str | None:
    pattern = re.compile(
        rf"(?ms)^  {re.escape(service_name)}:\n(?P<body>(?:    .*\n)+?)(?=^  [a-zA-Z0-9_]+:|\Z)"
    )
    match = pattern.search(compose_text)
    if match is None:
        return None
    return match.group("body")


def main() -> int:
    repo_root = Path(__file__).resolve().parents[2]
    failures = validate_release_gate_matrix()

    ci_workflow = repo_root / ".github/workflows/ci.yml"
    ci_text = _load_text(ci_workflow)
    ci_run_commands = _extract_run_commands(ci_text)
    for step in ci_gate_steps():
        if step.command not in ci_run_commands:
            failures.append(
                f".github/workflows/ci.yml missing CI gate command from matrix: {step.command!r}"
            )

    compose_file = repo_root / "compose.yml"
    compose_text = _load_text(compose_file)
    admin_block = _extract_compose_service_block(compose_text, "admin")
    if admin_block is None:
        failures.append("compose.yml missing admin service block.")
    elif 'command: ["bootstrap", "--smoke-in-process"]' not in admin_block:
        failures.append(
            "compose.yml admin service must pin command to bootstrap --smoke-in-process."
        )
    elif 'profiles: ["full"]' not in admin_block:
        failures.append(
            "compose.yml admin service must contain full profile entry for release smoke workflow."
        )

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
