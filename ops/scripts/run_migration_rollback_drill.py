"""Run migration validation + rollback drill and emit evidence JSON."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from openqilin.apps.admin_cli import (
    DEFAULT_ROLLBACK_DRILL_EVIDENCE,
    RollbackMode,
    build_migration_drill_evidence_payload,
    run_migration_rollback_drill,
    write_migration_drill_evidence,
)


def _build_parser() -> argparse.ArgumentParser:
    repo_root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(
        description="Run OpenQilin migration validation and rollback drill workflow."
    )
    parser.add_argument(
        "--rollback-mode",
        choices=[RollbackMode.RESTORE.value, RollbackMode.DOWNGRADE.value],
        default=RollbackMode.RESTORE.value,
        help="Rollback mode. Use downgrade only on disposable databases.",
    )
    parser.add_argument(
        "--rollback-revision",
        default="-1",
        help="Downgrade revision target when --rollback-mode=downgrade.",
    )
    parser.add_argument(
        "--allow-downgrade-destructive",
        action="store_true",
        help="Explicitly allow destructive downgrade mode (disposable databases only).",
    )
    parser.add_argument(
        "--restore-reference",
        default=None,
        help="Backup/snapshot reference required for --rollback-mode=restore.",
    )
    parser.add_argument(
        "--release-version",
        default="0.1.0-dev",
        help="Release version recorded in evidence output.",
    )
    parser.add_argument(
        "--operator",
        default="unknown_operator",
        help="Operator identity recorded in evidence output.",
    )
    parser.add_argument(
        "--reason",
        default="release_readiness_drill",
        help="Reason recorded in evidence output.",
    )
    parser.add_argument(
        "--database-url",
        default=None,
        help="Optional database URL override used for drill execution.",
    )
    parser.add_argument(
        "--alembic-ini",
        type=Path,
        default=repo_root / "alembic.ini",
        help="Path to alembic.ini used for migration execution.",
    )
    parser.add_argument(
        "--evidence-output",
        type=Path,
        default=DEFAULT_ROLLBACK_DRILL_EVIDENCE,
        help="Destination JSON path for drill evidence.",
    )
    return parser


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()
    rollback_mode = RollbackMode(args.rollback_mode)

    results, resolved_database_url = run_migration_rollback_drill(
        alembic_ini_path=args.alembic_ini,
        database_url=args.database_url,
        rollback_mode=rollback_mode,
        rollback_revision=args.rollback_revision,
        restore_reference=args.restore_reference,
        allow_downgrade_destructive=args.allow_downgrade_destructive,
    )
    payload = build_migration_drill_evidence_payload(
        release_version=args.release_version,
        operator=args.operator,
        reason=args.reason,
        rollback_mode=rollback_mode,
        rollback_revision=args.rollback_revision,
        restore_reference=args.restore_reference,
        database_url=resolved_database_url or "unresolved",
        results=results,
    )
    output_path = write_migration_drill_evidence(payload, args.evidence_output)

    for result in results:
        status = "OK" if result.success else "FAIL"
        print(f"[{status}] {result.name}: {result.details}")
    print(f"[INFO] rollback_drill_evidence: {output_path}")
    return 0 if all(result.success for result in results) else 1


if __name__ == "__main__":
    sys.exit(main())
