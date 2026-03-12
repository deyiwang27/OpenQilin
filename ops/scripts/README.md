# ops/scripts

Operational helper scripts for diagnostics and maintenance.

Current baseline scripts:
- `admin-entrypoint.sh`: container entrypoint for admin one-shot commands used by `compose.yml`.
- `check_spec_integrity.py`: validates reliability-profile doc constants and canonical error-code casing to catch spec drift in CI.
- `run_migration_rollback_drill.py`: executes migration validation + rollback drill and writes evidence JSON.
- `check_migration_rollback_readiness.py`: enforces rollback-drill policy/gate integrity in CI.
