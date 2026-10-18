"""Tests for open source license compliance, notices, and attribution integrity."""

from __future__ import annotations

from pathlib import Path


def test_root_license_exists():
    """Verify that root LICENSE file exists and is AGPL-3.0."""
    repo_root = Path(__file__).resolve().parents[2]
    license_path = repo_root / "LICENSE"
    assert license_path.exists(), "LICENSE file must exist at repo root"
    content = license_path.read_text(encoding="utf-8")
    assert "GNU AFFERO GENERAL PUBLIC LICENSE" in content
    assert "Version 3" in content


def test_notice_file_integrity():
    """Verify that NOTICE file exists and credits key upstream projects and foundations."""
    repo_root = Path(__file__).resolve().parents[2]
    notice_path = repo_root / "NOTICE"
    assert notice_path.exists(), "NOTICE file must exist at repo root"
    content = notice_path.read_text(encoding="utf-8")
    assert "Cohezion AI Swarm Orchestration Framework" in content
    assert "Mike Anderson and Cohezion Contributors" in content
    assert "Python Software Foundation" in content
    assert "Apache Software Foundation" in content
    assert "AutoHarness" in content
    assert "LLM-to-Flow Distillation" in content
    assert "Terminal-RSI" in content
    assert "Stafford Beer" in content
    assert "W. Ross Ashby" in content


def test_attribution_file_coverage():
    """Verify that ATTRIBUTION.md documents academic citations, competitions, and benchmarks."""
    repo_root = Path(__file__).resolve().parents[2]
    attr_path = repo_root / "ATTRIBUTION.md"
    assert attr_path.exists(), "ATTRIBUTION.md must exist at repo root"
    content = attr_path.read_text(encoding="utf-8")

    # Academic & Theoretical Foundations
    assert "arXiv:2603.03329v1" in content  # AutoHarness
    assert "arXiv:2610.17246" in content  # LLM-to-Flow Distillation
    assert "arXiv:2610.22192" in content  # Terminal-RSI
    assert "Viable System Model" in content  # Stafford Beer
    assert "Requisite Variety" in content  # Ashby
    assert "Conant-Ashby Theorem" in content
    assert "Poincaré" in content

    # Kaggle Competitions & Datasets
    assert "ARC Prize" in content
    assert "CASMI26" in content
    assert "RSNA Knee" in content
    assert "Name That LLM" in content
    assert "Gemma 4 Developer Agent" in content

    # Industry-Standard Benchmarks
    assert "SWE-bench" in content
    assert "GAIA" in content
    assert "MLPerf" in content

    # Hardware & Platforms
    assert "AMD ROCm & XDNA 2" in content
    assert "SurrealDB" in content


def test_third_party_licenses_sbom_manifest():
    """Verify that THIRD_PARTY_LICENSES.md contains SBOM with verified license compatibility."""
    repo_root = Path(__file__).resolve().parents[2]
    sbom_path = repo_root / "THIRD_PARTY_LICENSES.md"
    assert sbom_path.exists(), "THIRD_PARTY_LICENSES.md must exist at repo root"
    content = sbom_path.read_text(encoding="utf-8")

    assert "Software Bill of Materials (SBOM)" in content
    assert "AGPL-3.0-or-later" in content
    assert "Permissive Open Source" in content
    assert "Verified Compatible" in content
    assert "Total Python Packages Audited" in content
    assert "Internal Native Rust Components" in content


def test_internal_rust_crates_license_declaration():
    """Verify that all internal Rust crates declare valid license expressions."""
    repo_root = Path(__file__).resolve().parents[2]
    cargo_files = list(repo_root.glob("src/**/Cargo.toml"))
    assert len(cargo_files) >= 3, "Expected at least 3 internal Rust crates"

    for cargo_path in cargo_files:
        content = cargo_path.read_text(encoding="utf-8")
        assert 'license = "AGPL-3.0-or-later OR MIT"' in content, (
            f"Crate {cargo_path} must declare AGPL-3.0-or-later OR MIT license"
        )


def test_sbom_check_cli_gate():
    """Verify that scripts/ci/generate_sbom_and_licenses.py --check passes without drift."""
    from scripts.ci.generate_sbom_and_licenses import main as sbom_main

    exit_code = sbom_main(["--check"])
    assert exit_code == 0, "SBOM check CLI gate must exit with code 0 on compliant codebase"
