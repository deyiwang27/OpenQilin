# ops/scripts

Operational helper scripts for diagnostics and maintenance.

Current baseline scripts:
- `admin-entrypoint.sh`: container entrypoint for admin one-shot commands used by `compose.yml`.
- `check_spec_integrity.py`: validates reliability-profile doc constants and canonical error-code casing to catch spec drift in CI.
