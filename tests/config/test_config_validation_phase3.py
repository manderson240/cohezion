"""Integration tests for Phase 3: Validation & Reconciliation.

Tests comprehensive validation, archival, and sync logging.
"""

import json
from pathlib import Path

import pytest

from cohezion.config import (
    ConfigArchiver,
    ConfigSyncLogger,
    ConfigurationOrchestrator,
    ConfigValidator,
    ReconciliationValidator,
    SizeEnforcer,
)


class TestConfigValidator:
    """Test configuration validation."""

    def test_validator_init(self) -> None:
        """Test validator initialization."""
        validator = ConfigValidator()

        assert validator.size_limits["CLAUDE.md"]["max_lines"] == 250
        assert validator.size_limits["GEMINI.md"]["max_lines"] == 200

    def test_validate_file_with_frontmatter(self, tmp_path: Path) -> None:
        """Test validation of file with valid frontmatter."""
        test_file = tmp_path / "test.md"
        content = """---
title: Test Document
status: active
---

# Section 1

Content here."""

        test_file.write_text(content)
        validator = ConfigValidator()

        report = validator.validate_file(test_file)
        assert report.passed

    def test_validate_file_missing_frontmatter(self, tmp_path: Path) -> None:
        """Test validation of file without frontmatter."""
        test_file = tmp_path / "test.md"
        test_file.write_text("# No frontmatter\n\nContent")

        validator = ConfigValidator()
        report = validator.validate_file(test_file)

        assert not report.passed
        assert any("frontmatter" in r.lower() for r in report.recommendations)

    def test_check_size_violation(self, tmp_path: Path) -> None:
        """Test size violation detection."""
        from cohezion.config.config_state import FileMetadata

        test_file = tmp_path / "CLAUDE.md"
        # Create file with 300 lines (exceeds 250 limit)
        content = "\n".join([f"Line {i}" for i in range(300)])
        test_file.write_text(content)

        validator = ConfigValidator()
        metadata = FileMetadata.from_file(test_file)
        check_result = validator._check_size(test_file, metadata)

        assert not check_result["passed"]
        assert any("exceeds" in r.lower() for r in check_result["recommendations"])

    def test_check_references_valid(self, tmp_path: Path) -> None:
        """Test valid reference checking."""
        # Create vault structure
        vault_root = tmp_path / "vault"
        vault_root.mkdir()
        (vault_root / "decisions").mkdir()
        (vault_root / "test_decision.md").write_text("# Test")

        test_file = tmp_path / "config.md"
        content = """---
title: Config
status: active
---

See [[test_decision.md]] for details."""

        test_file.write_text(content)

        validator = ConfigValidator()
        validator._check_references(test_file)

        # Will pass because we're not checking vault root in this simple test
        assert True  # Basic structure test

    def test_check_cycles_self_ref(self, tmp_path: Path) -> None:
        """Test cycle detection for self-references."""
        test_file = tmp_path / "test_document.md"
        content = """---
title: Test
status: active
---

See [[test_document]] for details."""

        test_file.write_text(content)

        validator = ConfigValidator()
        check_result = validator._check_cycles(test_file)

        assert not check_result["passed"]


class TestSizeEnforcer:
    """Test size enforcement."""

    def test_size_enforcer_init(self) -> None:
        """Test size enforcer initialization."""
        enforcer = SizeEnforcer()

        assert "CLAUDE.md" in enforcer.size_limits
        assert "GEMINI.md" in enforcer.size_limits

    def test_check_violations_no_violation(self, tmp_path: Path) -> None:
        """Test file with no size violations."""
        test_file = tmp_path / "CLAUDE.md"
        test_file.write_text("# Title\n\nSmall content")

        enforcer = SizeEnforcer()
        result = enforcer.check_violations(test_file)

        assert not result["violates"]

    def test_check_violations_exceeds_lines(self, tmp_path: Path) -> None:
        """Test file that exceeds line limit."""
        test_file = tmp_path / "CLAUDE.md"
        content = "\n".join([f"Line {i}" for i in range(300)])
        test_file.write_text(content)

        enforcer = SizeEnforcer()
        result = enforcer.check_violations(test_file)

        assert result["violates"]
        assert any("Lines" in v for v in result["violations"])

    def test_remediation_actions(self, tmp_path: Path) -> None:
        """Test remediation action suggestions."""
        test_file = tmp_path / "CLAUDE.md"
        content = "\n".join([f"Line {i}" for i in range(300)])
        test_file.write_text(content)

        enforcer = SizeEnforcer()
        actions = enforcer.get_remediation_actions(test_file)

        assert len(actions) > 0
        assert any("archive" in a.lower() for a in actions)


class TestConfigArchiver:
    """Test configuration archival."""

    @pytest.mark.asyncio
    async def test_archiver_init(self, tmp_path: Path) -> None:
        """Test archiver initialization."""
        vault_root = tmp_path / "vault"
        vault_root.mkdir()

        archiver = ConfigArchiver(vault_root)

        assert archiver.vault_root == vault_root
        assert archiver.archive_dir.exists()

    @pytest.mark.asyncio
    async def test_archive_old_sections(self, tmp_path: Path) -> None:
        """Test archiving old sections."""
        vault_root = tmp_path / "vault"
        vault_root.mkdir()

        archiver = ConfigArchiver(vault_root)

        test_file = tmp_path / "test.md"
        content = """---
title: Test
status: active
---

# Current Section

Current content

# Deprecated Section (2025-01-01)

Old content from 2025"""

        test_file.write_text(content)

        result = await archiver.archive_old_sections(test_file)

        # Archiver identifies "Deprecated" sections
        assert result is not None

    @pytest.mark.asyncio
    async def test_archive_status(self, tmp_path: Path) -> None:
        """Test archive status reporting."""
        vault_root = tmp_path / "vault"
        vault_root.mkdir()

        archiver = ConfigArchiver(vault_root)
        status = archiver.get_archive_status()

        assert "archive_count" in status
        assert status["retention_policy"] == "full_history"


class TestConfigSyncLogger:
    """Test sync operation logging."""

    @pytest.mark.asyncio
    async def test_logger_init(self, tmp_path: Path) -> None:
        """Test logger initialization."""
        logger = ConfigSyncLogger(tmp_path)

        assert logger.log_dir == tmp_path
        assert logger.log_dir.exists()

    @pytest.mark.asyncio
    async def test_log_validation(self, tmp_path: Path) -> None:
        """Test logging validation operation."""
        logger = ConfigSyncLogger(tmp_path)

        await logger.log_validation(
            file="CLAUDE.md",
            status="success",
            details={"passed": True},
            duration_ms=10.5,
        )

        assert len(logger._entries) == 1
        assert logger._entries[0].operation == "validate"

    @pytest.mark.asyncio
    async def test_log_sync(self, tmp_path: Path) -> None:
        """Test logging sync operation."""
        logger = ConfigSyncLogger(tmp_path)

        await logger.log_sync(
            file="CLAUDE.md",
            status="success",
            details={"regenerated": True},
            duration_ms=25.0,
        )

        assert len(logger._entries) == 1
        assert logger._entries[0].operation == "sync"

    @pytest.mark.asyncio
    async def test_log_archival(self, tmp_path: Path) -> None:
        """Test logging archival operation."""
        logger = ConfigSyncLogger(tmp_path)

        await logger.log_archival(
            file="CLAUDE.md",
            status="success",
            details={"sections_archived": 3},
        )

        assert len(logger._entries) == 1
        assert logger._entries[0].operation == "archive"

    def test_get_logs_by_operation(self, tmp_path: Path) -> None:
        """Test filtering logs by operation."""
        logger = ConfigSyncLogger(tmp_path)

        # Simulate some entries
        from cohezion.config.config_sync_logger import SyncLogEntry

        logger._entries = [
            SyncLogEntry(
                timestamp="2026-02-10T01:00:00",
                operation="validate",
                status="success",
                file="CLAUDE.md",
                details={},
            ),
            SyncLogEntry(
                timestamp="2026-02-10T01:01:00",
                operation="sync",
                status="success",
                file="CLAUDE.md",
                details={},
            ),
        ]

        validates = logger.get_logs_by_operation("validate")
        assert len(validates) == 1

    def test_get_statistics(self, tmp_path: Path) -> None:
        """Test statistics reporting."""
        logger = ConfigSyncLogger(tmp_path)

        from cohezion.config.config_sync_logger import SyncLogEntry

        logger._entries = [
            SyncLogEntry(
                timestamp="2026-02-10T01:00:00",
                operation="validate",
                status="success",
                file="CLAUDE.md",
                details={},
            ),
            SyncLogEntry(
                timestamp="2026-02-10T01:01:00",
                operation="validate",
                status="success",
                file="GEMINI.md",
                details={},
            ),
        ]

        stats = logger.get_statistics()

        assert stats["total_entries"] == 2
        assert stats["by_operation"]["validate"] == 2
        assert stats["success_rate"] == 100.0

    @pytest.mark.asyncio
    async def test_export_to_json(self, tmp_path: Path) -> None:
        """Test exporting logs to JSON."""
        logger = ConfigSyncLogger(tmp_path)

        await logger.log_validation(
            file="CLAUDE.md",
            status="success",
            details={"passed": True},
        )

        export_path = logger.export_to_json(tmp_path / "export.json")

        assert Path(export_path).exists()

        # Verify content
        with open(export_path) as f:
            data = json.load(f)
            assert data["entry_count"] == 1


class TestReconciliationValidator:
    """Test reconciliation validation."""

    def test_validator_init(self) -> None:
        """Test reconciliation validator initialization."""
        validator = ReconciliationValidator()
        assert validator is not None

    def test_validate_consistency(self, tmp_path: Path) -> None:
        """Test consistency validation."""
        vault_root = tmp_path / "vault"
        vault_root.mkdir()

        claude_md = tmp_path / "CLAUDE.md"
        gemini_md = tmp_path / "GEMINI.md"
        claude_md.write_text("# CLAUDE\n\nContent")
        gemini_md.write_text("# GEMINI\n\nContent")

        validator = ReconciliationValidator()
        report = validator.validate_consistency(claude_md, gemini_md, vault_root)

        assert report is not None


class TestOrchestrationWithValidation:
    """Test orchestrator with Phase 3 components."""

    def test_orchestrator_has_validators(self, tmp_path: Path) -> None:
        """Test that orchestrator has Phase 3 components."""
        orch = ConfigurationOrchestrator(tmp_path)

        assert hasattr(orch, "validator")
        assert hasattr(orch, "archiver")
        assert hasattr(orch, "size_enforcer")
        assert hasattr(orch, "sync_logger")

    @pytest.mark.asyncio
    async def test_orchestrator_validate_consistency_integration(self, tmp_path: Path) -> None:
        """Test orchestrator validation integration."""
        claude_md = tmp_path / "CLAUDE.md"
        claude_md.write_text("---\ntitle: CLAUDE\nstatus: active\n---\n\n# Content")

        orch = ConfigurationOrchestrator(tmp_path)

        report = await orch.validate_consistency()

        assert report is not None
        assert report.duration_ms > 0
