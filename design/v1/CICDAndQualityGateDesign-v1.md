# OpenQilin v1 - CI/CD and Quality Gate Design

## 1. Scope
- Define the CI/CD process for v1 implementation.
- Define merge gates, release gates, and branch-quality expectations.

## 2. Branch and Merge Workflow
Recommended v1 workflow:
- short-lived feature branches
- pull request into protected default branch
- no direct commits to protected branch for implementation code

## 3. Mandatory PR Checks
- dependency install with `uv` in locked mode
- lint
- format check
- type check
- unit tests
- component tests
- contract tests
- spec/conformance integrity checks

## 4. Additional Checks For Relevant Changes
- integration tests when runtime-flow code changes
- migration validation when schema changes occur
- conformance smoke tests when governance-core behavior changes
- docs/design/spec drift check when contracts are modified

## 5. Quality Gates
Merge is blocked when:
- lint/format/type checks fail
- tests required by change scope fail
- lockfile drift is detected
- critical conformance checks fail
- migration forward-apply validation fails

Release is blocked when:
- critical conformance checks fail
- restore/recovery evidence is missing
- unresolved P0/P1 implementation blockers remain

## 6. CI Pipeline Stages
1. setup Python + `uv`
2. locked dependency sync
3. static checks
4. unit/component tests
5. contract tests
6. integration/conformance checks as required
7. build artifact/container validation

## 7. CD Posture
v1 initial posture:
- CI required immediately
- CD may remain manual/promotion-gated during early local-first development

Manual promotion gates should require:
- passing CI
- migration plan available
- config/secret readiness confirmed
- rollback path documented

## 8. Artifact Policy
- container build definitions should be reproducible from the repo
- build metadata should include version/provenance references
- release artifacts must be traceable to code + config baseline

## 9. Related Design Follow-Ups
- test layer details are in `TestStrategyAndLayout-v1.md`
- dependency management is in `PythonToolchainAndDependencyManagement-v1.md`
- release/rollback workflow is planned later in `ReleaseVersioningAndRollback-v1.md`
