"""Execute release-gate matrix steps in deterministic order."""

from __future__ import annotations

import argparse
import subprocess
import sys

from openqilin.release_readiness.gate_matrix import (
    ci_gate_steps,
    release_candidate_gate_steps,
    validate_release_gate_matrix,
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run OpenQilin release-gate command matrix.")
    parser.add_argument(
        "--scope",
        choices=("ci", "release-candidate"),
        default="ci",
        help="Matrix scope to run.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print commands only without executing them.",
    )
    return parser


def _resolve_steps(scope: str):
    if scope == "ci":
        return ci_gate_steps()
    return release_candidate_gate_steps()


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()
    failures = validate_release_gate_matrix()
    if failures:
        print("Release-gate matrix validation failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1

    steps = _resolve_steps(args.scope)
    if not steps:
        print(f"No release-gate steps resolved for scope: {args.scope}")
        return 1

    for step in steps:
        print(f"[STEP] {step.step_id}: {step.command}")
        if args.dry_run:
            continue
        completed = subprocess.run(step.command, shell=True, check=False)
        if completed.returncode != 0:
            print(
                f"[FAIL] {step.step_id}: command exited with {completed.returncode}; "
                f"criteria={step.success_criteria}"
            )
            return completed.returncode
        print(f"[OK] {step.step_id}")

    print(f"Release-gate scope '{args.scope}' completed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
