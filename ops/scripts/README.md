# ops/scripts

Operational helper scripts for diagnostics and maintenance.

Current baseline scripts:
- `admin-entrypoint.sh`: container entrypoint for admin one-shot commands used by `compose.yml`.
- `check_spec_integrity.py`: validates reliability-profile doc constants and canonical error-code casing to catch spec drift in CI.
- `run_migration_rollback_drill.py`: executes migration validation + rollback drill and writes evidence JSON.
- `check_migration_rollback_readiness.py`: enforces rollback-drill policy/gate integrity in CI.
- `run_release_gate_matrix.py`: executes deterministic CI/release-candidate gate command matrix.
- `check_release_gate_matrix.py`: validates matrix/workflow/compose/doc alignment for release-gate hardening.
- `run_release_artifact_packager.py`: generates release-candidate artifact bundle JSON and rendered promotion checklist markdown.
- `check_release_artifact_package.py`: validates release artifact package docs and promotion decision/rollback hooks.
- `run_m9_live_discord_acceptance.py`: runs M9 live-acceptance preflight checks, writes deterministic preflight-report JSON, and initializes evidence-manifest/notes-template artifacts for real Discord validation.
- `check_m9_live_acceptance_artifacts.py`: validates deterministic M9 live-acceptance artifact completeness before milestone closeout.
