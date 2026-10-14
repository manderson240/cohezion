"""Unit Tests for Cohezion REA Reverse Engineering Engine.
======================================================
Reference: morluto/rea (Reverse Engineer Anything).
"""

from __future__ import annotations

import io
import sys
import zipfile
from pathlib import Path
import pytest

from cohezion.reverse_engineering import (
    AnalysisSession,
    ArtifactInspector,
    EvidenceRecord,
    FacetAvailability,
    ProvenanceMarker,
    UnknownLedger,
    UnknownStatus,
)


def test_evidence_creation_and_provenance():
    """Verify EvidenceRecord content-addressing and untrusted provenance marking."""
    normalized = {"symbols": ["fn_a", "fn_b"], "architecture": "x86_64"}
    facets = {
        "symbols": FacetAvailability(available=True),
        "decompilation": FacetAvailability(available=False, reason="Engine not attached"),
    }
    record = EvidenceRecord.create(
        target_path="/tmp/fake_bin",
        operation="test_op",
        normalized_result=normalized,
        facet_availability=facets,
    )

    assert record.evidence_id.startswith("ev_")
    assert record.provenance.untrusted_content is True
    assert record.provenance.source == "analysis_target"
    assert record.facet_availability["symbols"].available is True
    assert record.facet_availability["decompilation"].available is False
    assert "Engine not attached" in str(record.facet_availability["decompilation"].reason)


def test_unknown_ledger_lifecycle():
    """Verify UnknownLedger progressive hypothesis tracking and resolution."""
    ledger = UnknownLedger()
    item = ledger.record_unknown(
        domain="binary_hardening",
        question="Is stack canary protection enabled?",
    )

    assert item.unknown_id.startswith("unk_")
    assert item.status == UnknownStatus.OPEN

    # Resolve unknown with empirical evidence
    resolved = ledger.resolve_unknown(
        unknown_id=item.unknown_id,
        resolution="__stack_chk_fail found in symbols",
        evidence_id="ev_12345",
    )

    assert resolved is not None
    assert resolved.status == UnknownStatus.RESOLVED
    assert "ev_12345" in resolved.evidence_links
    assert "__stack_chk_fail" in str(resolved.resolution)


def test_inspect_python_bytecode():
    """Verify AST and bytecode dissection."""
    code = """
import os
from math import sqrt

class Solver:
    \"\"\"Solves equations.\"\"\"
    def compute(self, x):
        return sqrt(x)
"""
    evidence = ArtifactInspector.inspect_python_bytecode(code)
    norm = evidence.normalized_result

    assert norm["function_count"] == 1
    assert norm["class_count"] == 1
    assert norm["functions"][0]["name"] == "compute"
    assert "math.sqrt" in norm["imports"]
    assert "os" in norm["imports"]
    assert evidence.facet_availability["ast_symbols"].available is True


def test_inspect_binary_layout(tmp_path: Path):
    """Verify ELF header parsing on a synthetic ELF binary."""
    # Construct minimal synthetic 64-bit ELF header
    # Magic: \x7fELF (4 bytes)
    # Class: 2 (64-bit), Data: 1 (Little endian), Version: 1, OS/ABI: 0, Pad: 8 bytes
    # Type: 2 (EXEC), Machine: 0x3E (x86_64), Version: 1, Entry: 0x401000 (8 bytes)
    elf_header = bytearray(b"\x7fELF\x02\x01\x01\x00" + b"\x00" * 8)
    elf_header.extend(b"\x02\x00")       # e_type = EXEC
    elf_header.extend(b"\x3e\x00")       # e_machine = x86_64
    elf_header.extend(b"\x01\x00\x00\x00") # e_version = 1
    elf_header.extend(b"\x00\x10\x40\x00\x00\x00\x00\x00") # e_entry = 0x401000
    elf_header.extend(b"\x00" * 32)      # Padding

    test_elf = tmp_path / "test_bin"
    test_elf.write_bytes(elf_header)

    evidence = ArtifactInspector.inspect_binary_layout(test_elf)
    norm = evidence.normalized_result

    assert norm["format"] == "ELF"
    assert norm["bitness"] == 64
    assert norm["endianness"] == "little"
    assert norm["architecture"] == "x86_64"
    assert norm["entrypoint"] == "0x401000"


def test_inspect_python_wheel_and_paged_views(tmp_path: Path):
    """Verify wheel inspection and session-retained paged view projection."""
    whl_path = tmp_path / "test_pkg-0.1.0-py3-none-any.whl"
    with zipfile.ZipFile(whl_path, "w") as z:
        z.writestr("test_pkg/__init__.py", "# init")
        z.writestr("test_pkg/core.py", "def run(): pass")
        z.writestr("test_pkg-0.1.0.dist-info/METADATA", "Name: test-pkg\nVersion: 0.1.0\nRequires-Dist: numpy>=1.20\n")
        z.writestr("test_pkg-0.1.0.dist-info/RECORD", "test_pkg/__init__.py,sha256=123,5\n")

    evidence = ArtifactInspector.inspect_python_wheel(whl_path)
    norm = evidence.normalized_result

    assert norm["package_name"] == "test-pkg"
    assert norm["version"] == "0.1.0"
    assert "numpy>=1.20" in norm["dependencies"]
    assert norm["total_files"] == 4

    # Test Session retention and Paged View projection
    session = AnalysisSession(session_id="test_sess")
    session.record_evidence(evidence)

    # Page 1: limit 2
    page1 = session.inspect_analysis_view(
        evidence_id=evidence.evidence_id,
        facet="files",
        offset=0,
        limit=2,
    )
    assert len(page1.items) == 2
    assert page1.next_offset == 2
    assert page1.is_truncated is True

    # Page 2: limit 2
    page2 = session.inspect_analysis_view(
        evidence_id=evidence.evidence_id,
        facet="files",
        offset=2,
        limit=2,
    )
    assert len(page2.items) == 2
    assert page2.next_offset is None
    assert page2.is_truncated is False
