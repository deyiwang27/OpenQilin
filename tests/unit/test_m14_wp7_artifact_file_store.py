"""M14-WP7 — Artifact file store unit tests."""

from __future__ import annotations

import hashlib
from pathlib import Path

from openqilin.agents.administrator.document_policy import DocumentPolicyEnforcer
from openqilin.data_access.artifact_file_store import ArtifactFileStore, ArtifactFileStoreError
from openqilin.observability.testing.stubs import InMemoryAuditWriter
from tests.testing.infra_stubs import InMemoryProjectArtifactRepository


def _make_enforcer(
    tmp_path: Path,
) -> tuple[DocumentPolicyEnforcer, ArtifactFileStore, InMemoryAuditWriter]:
    repo = InMemoryProjectArtifactRepository(system_root=tmp_path / "artifacts")
    audit_writer = InMemoryAuditWriter()
    file_store = ArtifactFileStore(system_root=tmp_path)
    enforcer = DocumentPolicyEnforcer(
        governance_repo=repo,
        audit_writer=audit_writer,
        trace_id_factory=lambda: "generated-trace",
        artifact_file_store=file_store,
    )
    return enforcer, file_store, audit_writer


class TestArtifactFileStore:
    def test_write_creates_file_at_canonical_path(self, tmp_path: Path) -> None:
        file_store = ArtifactFileStore(system_root=tmp_path)

        storage_uri, _ = file_store.write(
            project_id="proj-001",
            artifact_type="execution_plan",
            version_no=1,
            content_md="# Execution Plan\n\nHello",
        )

        expected_path = tmp_path / "projects" / "proj-001" / "execution_plan-v001.md"
        assert expected_path.exists()
        assert storage_uri.startswith("file://")
        assert storage_uri == f"file://{expected_path.resolve()}"

    def test_write_content_hash_matches_sha256(self, tmp_path: Path) -> None:
        file_store = ArtifactFileStore(system_root=tmp_path)
        content = "# Decision Log\n\nEntry"

        _, content_hash = file_store.write(
            project_id="proj-001",
            artifact_type="decision_log",
            version_no=1,
            content_md=content,
        )

        assert content_hash == hashlib.sha256(content.encode()).hexdigest()

    def test_read_returns_written_content(self, tmp_path: Path) -> None:
        file_store = ArtifactFileStore(system_root=tmp_path)
        content = "# Progress Report\n\nUpdate"
        storage_uri, _ = file_store.write(
            project_id="proj-001",
            artifact_type="progress_report",
            version_no=1,
            content_md=content,
        )

        assert file_store.read(storage_uri) == content

    def test_path_traversal_blocked_in_write(self, tmp_path: Path) -> None:
        file_store = ArtifactFileStore(system_root=tmp_path)

        try:
            file_store.write(
                project_id="../etc",
                artifact_type="execution_plan",
                version_no=1,
                content_md="blocked",
            )
        except ArtifactFileStoreError as exc:
            assert exc.code == "artifact_file_store_path_traversal"
        else:
            raise AssertionError("expected ArtifactFileStoreError for path traversal")

    def test_read_invalid_scheme_raises(self, tmp_path: Path) -> None:
        file_store = ArtifactFileStore(system_root=tmp_path)

        try:
            file_store.read("db://foo")
        except ArtifactFileStoreError as exc:
            assert exc.code == "artifact_file_store_scheme_invalid"
        else:
            raise AssertionError("expected ArtifactFileStoreError for invalid scheme")

    def test_read_missing_file_raises(self, tmp_path: Path) -> None:
        file_store = ArtifactFileStore(system_root=tmp_path)
        missing_path = tmp_path / "projects" / "proj-001" / "execution_plan-v001.md"

        try:
            file_store.read(f"file://{missing_path}")
        except ArtifactFileStoreError as exc:
            assert exc.code == "artifact_file_store_not_found"
        else:
            raise AssertionError("expected ArtifactFileStoreError for missing file")


class TestVerifyStorageUriHash:
    def test_verify_storage_uri_hash_match_passes(self, tmp_path: Path) -> None:
        enforcer, file_store, audit_writer = _make_enforcer(tmp_path)
        storage_uri, written_hash = file_store.write(
            project_id="proj-001",
            artifact_type="execution_plan",
            version_no=1,
            content_md="# Execution Plan\n\nCurrent",
        )

        result = enforcer.verify_storage_uri_hash(
            storage_uri=storage_uri,
            db_content_hash=written_hash,
            trace_id="trace-001",
        )

        assert result.integrity_ok is True
        assert result.denial_reason is None
        assert audit_writer.get_events() == ()

    def test_verify_storage_uri_hash_mismatch_denied(self, tmp_path: Path) -> None:
        enforcer, file_store, audit_writer = _make_enforcer(tmp_path)
        storage_uri, _ = file_store.write(
            project_id="proj-001",
            artifact_type="execution_plan",
            version_no=1,
            content_md="# Execution Plan\n\nCurrent",
        )

        result = enforcer.verify_storage_uri_hash(
            storage_uri=storage_uri,
            db_content_hash="wrong-hash",
            trace_id="trace-001",
        )

        assert result.integrity_ok is False
        assert "content_hash mismatch" in (result.denial_reason or "")
        event = audit_writer.get_events()[-1]
        assert event.event_type == "hash_integrity_failure"
        assert event.rule_ids == ("STR-007", "STR-010")

    def test_verify_storage_uri_hash_file_missing_denied(self, tmp_path: Path) -> None:
        enforcer, _, audit_writer = _make_enforcer(tmp_path)
        missing_path = tmp_path / "projects" / "proj-001" / "execution_plan-v001.md"

        result = enforcer.verify_storage_uri_hash(
            storage_uri=f"file://{missing_path}",
            db_content_hash="expected-hash",
            trace_id="trace-001",
        )

        assert result.integrity_ok is False
        assert "file read error" in (result.denial_reason or "")
        event = audit_writer.get_events()[-1]
        assert event.event_type == "hash_integrity_failure"
        assert event.rule_ids == ("STR-007", "STR-010")

    def test_verify_storage_uri_hash_no_file_store_returns_ok(self, tmp_path: Path) -> None:
        repo = InMemoryProjectArtifactRepository(system_root=tmp_path / "artifacts")
        audit_writer = InMemoryAuditWriter()
        enforcer = DocumentPolicyEnforcer(
            governance_repo=repo,
            audit_writer=audit_writer,
            trace_id_factory=lambda: "generated-trace",
            artifact_file_store=None,
        )

        result = enforcer.verify_storage_uri_hash(
            storage_uri="file:///tmp/not-checked.md",
            db_content_hash="not-checked",
            trace_id="trace-001",
        )

        assert result.integrity_ok is True
        assert result.denial_reason is None
        assert audit_writer.get_events() == ()
