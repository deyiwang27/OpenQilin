"""Static integrity checks for migration/rollback readiness gates."""

from __future__ import annotations

import sys
from pathlib import Path


def _load_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def main() -> int:
    repo_root = Path(__file__).resolve().parents[2]
    failures: list[str] = []

    migration_versions = sorted((repo_root / "migrations" / "versions").glob("*.py"))
    migration_versions = [path for path in migration_versions if path.name != ".gitkeep"]
    if not migration_versions:
        failures.append("migrations/versions must contain at least one migration file.")

    for path in migration_versions:
        text = _load_text(path)
        if "def upgrade() -> None" not in text:
            failures.append(f"{path.relative_to(repo_root)} is missing upgrade() contract.")
        if "def downgrade() -> None" not in text:
            failures.append(f"{path.relative_to(repo_root)} is missing downgrade() contract.")

    release_doc = repo_root / "implementation/v1/quality/ReleaseVersioningAndRollback-v1.md"
    release_text = _load_text(release_doc)
    for snippet in (
        "do not rely on destructive down-migrations in v1",
        "rollback-drill",
        "restore-from-backup",
    ):
        if snippet not in release_text:
            failures.append(
                f"{release_doc.relative_to(repo_root)} missing rollback policy snippet: {snippet!r}"
            )

    workflow = repo_root / ".github/workflows/ci.yml"
    workflow_text = _load_text(workflow)
    if "ops/scripts/check_migration_rollback_readiness.py" not in workflow_text:
        failures.append(
            ".github/workflows/ci.yml must run ops/scripts/check_migration_rollback_readiness.py"
        )

    if failures:
        print("Migration/rollback readiness checks failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("Migration/rollback readiness checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
