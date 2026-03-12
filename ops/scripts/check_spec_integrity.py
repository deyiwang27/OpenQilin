"""Repo-local integrity checks for spec/design constants and conventions."""

from __future__ import annotations

import re
import sys
from pathlib import Path


def _load_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def main() -> int:
    repo_root = Path(__file__).resolve().parents[2]
    failures: list[str] = []

    reliability_docs = [
        repo_root / "spec/orchestration/communication/AgentCommunicationA2A.md",
        repo_root / "spec/orchestration/communication/AgentCommunicationACP.md",
        repo_root / "spec/orchestration/control/TaskOrchestrator.md",
        repo_root / "design/v1/components/CommunicationGatewayComponentDesign-v1.md",
        repo_root / "design/v1/sequences/SEQ-0003-A2A-ACP-Reliability-Lifecycle.md",
        repo_root / "design/v1/adr/ADR-0003-A2A-ACP-Reliability-Pipeline.md",
    ]
    disallowed_max_attempts_snippets = (
        '"max_attempts": 5',
        "`max_attempts`: `5`",
        "max_attempts=5",
    )

    for path in reliability_docs:
        text = _load_text(path)
        for snippet in disallowed_max_attempts_snippets:
            if snippet in text:
                failures.append(
                    f"{path.relative_to(repo_root)} still contains deprecated reliability profile value: {snippet!r}"
                )
        if "max_attempts" not in text:
            failures.append(
                f"{path.relative_to(repo_root)} does not contain max_attempts; expected reliability profile lock."
            )

    error_doc = repo_root / "spec/cross-cutting/runtime/ErrorCodesAndHandling.md"
    error_text = _load_text(error_doc)

    if "lower snake-case" not in error_text:
        failures.append(
            "spec/cross-cutting/runtime/ErrorCodesAndHandling.md must define canonical code casing as lower snake-case."
        )

    uppercase_snake_codes = sorted(set(re.findall(r"`([A-Z][A-Z0-9]*_[A-Z0-9_]+)`", error_text)))
    if uppercase_snake_codes:
        failures.append(
            "spec/cross-cutting/runtime/ErrorCodesAndHandling.md contains non-canonical uppercase codes: "
            + ", ".join(uppercase_snake_codes)
        )

    if not re.search(r"`[a-z][a-z0-9]*(?:_[a-z0-9]+)+`", error_text):
        failures.append(
            "spec/cross-cutting/runtime/ErrorCodesAndHandling.md does not contain lower snake-case canonical codes."
        )

    if failures:
        print("Spec integrity checks failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("Spec integrity checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
