#!/usr/bin/env sh
set -eu

cd /workspace

# Keep admin one-shot commands runnable in baseline containers.
# Install project runtime dependencies plus Alembic for migrate/bootstrap commands.
python -m pip install --disable-pip-version-check --quiet -e /workspace alembic
export PYTHONPATH=/workspace/src

exec python -m openqilin.apps.admin_cli "$@"
