#!/usr/bin/env sh
set -eu

cd /workspace

# Keep admin one-shot commands runnable in baseline containers.
python -m pip install --disable-pip-version-check --quiet typer
export PYTHONPATH=/workspace/src

exec python -m openqilin.apps.admin_cli "$@"
