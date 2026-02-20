"""Tests for the broken link resolver module."""

import pytest
from vault_linker.resolver import LinkResolver


def test_case_insensitive_match():
    """Test case-insensitive exact matching."""
    existing_files = ["agentic-ai", "quantum-sensors", "dark-matter"]
    resolver = LinkResolver(existing_files)

    # Should match with different case
    matches = resolver.resolve_link("Agentic Ai")
    assert matches[0]["target"] == "agentic-ai"
    assert matches[0]["confidence"] >= 0.8


def test_slug_normalization():
    """Test slug normalization (spaces to hyphens, special chars removed)."""
    existing_files = ["agent-architecture", "quantum-computing"]
    resolver = LinkResolver(existing_files)

    # Spaces to hyphens
    matches = resolver.resolve_link("agent architecture")
    assert matches[0]["target"] == "agent-architecture"

    # Special characters
    matches = resolver.resolve_link("Agent_Architecture")
    assert matches[0]["target"] == "agent-architecture"


def test_date_prefix_stripping():
    """Test stripping date prefixes from links."""
    existing_files = ["phase-completion-pattern", "implementation-ready"]
    resolver = LinkResolver(existing_files)

    # Link with date prefix should match file without prefix
    matches = resolver.resolve_link("2026-02-14-phase-completion-pattern")
    assert matches[0]["target"] == "phase-completion-pattern"
    assert matches[0]["confidence"] >= 0.8


def test_partial_match_constrained():
    """Test constrained partial matching."""
    existing_files = ["dark-matter-detection", "quantum-entanglement"]
    resolver = LinkResolver(existing_files)

    # Full segment match should work
    matches = resolver.resolve_link("dark-matter")
    assert len(matches) > 0
    assert "dark-matter-detection" in [m["target"] for m in matches]

    # Partial segment should NOT auto-apply (confidence < 0.8)
    matches = resolver.resolve_link("ai")
    # Should either have no matches or low confidence
    if matches:
        assert matches[0]["confidence"] < 0.8


def test_no_match():
    """Test behavior when no match is found."""
    existing_files = ["file1", "file2"]
    resolver = LinkResolver(existing_files)

    matches = resolver.resolve_link("completely-different")
    assert len(matches) == 0


def test_confidence_scoring():
    """Test that confidence scores are assigned correctly."""
    existing_files = ["exact-match", "partial-match-file"]
    resolver = LinkResolver(existing_files)

    # Exact match should have higher confidence
    exact_matches = resolver.resolve_link("exact-match")
    partial_matches = resolver.resolve_link("partial")

    if exact_matches and partial_matches:
        assert exact_matches[0]["confidence"] > partial_matches[0]["confidence"]


def test_multiple_matches_ranked():
    """Test that multiple matches are ranked by confidence."""
    existing_files = ["dark-matter", "dark-matter-detection", "dark-energy"]
    resolver = LinkResolver(existing_files)

    matches = resolver.resolve_link("dark-matter")

    # Should return multiple matches, ranked by confidence
    assert len(matches) >= 1
    # Exact match should be first
    assert matches[0]["target"] == "dark-matter"

    # Confidence should be descending
    for i in range(len(matches) - 1):
        assert matches[i]["confidence"] >= matches[i + 1]["confidence"]
