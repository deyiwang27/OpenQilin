# OpenQilin v1 - Python Toolchain and Dependency Management

## 1. Scope
- Define the authoritative Python toolchain baseline for v1 implementation.
- Lock `uv` as the dependency, virtual environment, and command runner tool.
- Replace `pip` + `requirements.txt` as the primary developer workflow.

## 2. v1 Decision
Python runtime baseline:
- Python `3.12`

Package/dependency manager:
- `uv`

Authoritative project metadata:
- root `pyproject.toml`

Authoritative lockfile:
- root `uv.lock`

v1 packaging posture:
- single Python project at repo root
- one shared lockfile for all v1 apps and workers
- multiple runnable entrypoints under one package tree

## 3. Why This Baseline
- `uv` gives one tool for environment creation, dependency resolution, lockfile management, and command execution.
- v1 is local-first and should optimize for low-friction bootstrap and reproducibility.
- a single root project is simpler than a multi-package workspace for initial implementation.

## 4. Required Rules
- `pyproject.toml` is the only source of truth for Python dependencies.
- `uv.lock` is committed to the repository.
- `requirements.txt` is not maintained as a primary dependency artifact.
- direct `pip install ...` into the project environment is not part of the supported workflow.
- all local commands should run through `uv run ...`.

## 5. Dependency Group Strategy
Minimum dependency groups:
- `default`: runtime dependencies
- `dev`: local development helpers
- `test`: test-only dependencies
- `lint`: lint/format/type-check tools
- `ops`: migration/admin/bootstrap tooling if separated

Recommended conventions:
- keep runtime dependencies minimal
- keep provider-specific optional packages behind explicit groups when possible
- avoid hidden global tooling assumptions

## 6. Expected Root Files
- `pyproject.toml`
- `uv.lock`
- `.python-version` or equivalent documented Python version pin

## 7. Standard Developer Commands
Environment bootstrap:
```bash
uv sync
```

Run API app:
```bash
uv run python -m openqilin.apps.api
```

Run orchestrator worker:
```bash
uv run python -m openqilin.apps.orchestrator_worker
```

Run tests:
```bash
uv run pytest
```

Run lint/type checks:
```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy .
```

## 8. Migration From `pip` / `requirements.txt`
Supported v1 posture:
- no new `requirements.txt` files should be introduced for core implementation
- if an external deployment tool temporarily needs exported requirements, export from `uv` rather than hand-maintaining files

## 9. CI Expectations
- CI installs Python and `uv`
- CI restores/cacheable `uv` artifacts where practical
- CI uses `uv sync --frozen` or equivalent locked install mode
- CI fails if lockfile and `pyproject.toml` drift

## 10. Related Design Follow-Ups
- framework/library choices are defined separately in `ImplementationFrameworkSelection-v1.md`
- repo structure is defined separately in `RepoStructureAndPackageLayout-v1.md`
- CI/CD process is defined separately in `CICDAndQualityGateDesign-v1.md`
