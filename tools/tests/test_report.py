"""Tests for ReportGenerator bidirectional gap section."""

import json
from pathlib import Path

import pytest


def make_md(tmp_path: Path, name: str, tags: list[str], links: list[str] = None) -> Path:
    tags_yaml = json.dumps(tags)
    links_str = "\n".join(f"[[{lnk}]]" for lnk in (links or []))
    body = f"---\ntitle: {name}\ntags: {tags_yaml}\n---\n\ncontent\n\n{links_str}\n"
    p = tmp_path / f"{name}.md"
    p.write_text(body, encoding="utf-8")
    return p


class TestBidirectionalGapReport:
    def _make_report(self, tmp_path):
        from vault_linker.parser import VaultParser
        from vault_linker.report import ReportGenerator

        vp = VaultParser()
        files_index, link_graph = vp.walk_vault(tmp_path)
        broken_links = vp.classify_broken_links(files_index, link_graph)
        reporter = ReportGenerator(files_index, link_graph, broken_links)
        return reporter.generate_report()

    def test_bidirectional_section_present(self, tmp_path):
        make_md(tmp_path, "paper-a", ["ml"], links=["paper-b"])
        make_md(tmp_path, "paper-b", ["ml"])  # links to paper-a not present

        report = self._make_report(tmp_path)

        assert "## Bidirectional Gaps" in report

    def test_bidirectional_section_shows_gap(self, tmp_path):
        # paper-a → paper-b but paper-b ↛ paper-a
        make_md(tmp_path, "paper-a", ["ml"], links=["paper-b"])
        make_md(tmp_path, "paper-b", ["ml"])

        report = self._make_report(tmp_path)

        # paper-b should appear in the gaps section (it has an incoming link not returned)
        assert "paper-b" in report

    def test_no_gaps_when_all_bidirectional(self, tmp_path):
        # Both link to each other → no gaps
        make_md(tmp_path, "paper-a", ["ml"], links=["paper-b"])
        make_md(tmp_path, "paper-b", ["ml"], links=["paper-a"])

        report = self._make_report(tmp_path)

        assert "## Bidirectional Gaps" in report
        # Section should indicate no gaps
        assert "no bidirectional gaps" in report.lower() or "0 files" in report.lower()

    def test_top_20_limit(self, tmp_path):
        # Create 25 files that all point to target but target doesn't link back
        make_md(tmp_path, "target", ["ml"])
        for i in range(25):
            make_md(tmp_path, f"source-{i:02d}", ["ml"], links=["target"])

        report = self._make_report(tmp_path)

        # Should list at most 20 entries
        gap_section = ""
        in_section = False
        for line in report.splitlines():
            if "## Bidirectional Gaps" in line:
                in_section = True
            elif line.startswith("## ") and in_section:
                break
            elif in_section:
                gap_section += line + "\n"

        list_items = [l for l in gap_section.splitlines() if l.strip().startswith("|") and "---" not in l and "File" not in l]
        assert len(list_items) <= 20

    def test_existing_report_sections_preserved(self, tmp_path):
        make_md(tmp_path, "paper-a", ["ml"], links=["paper-b"])
        make_md(tmp_path, "paper-b", ["ml"])

        report = self._make_report(tmp_path)

        # Existing sections should still be present
        assert "## Summary" in report
        assert "## Broken Links by Category" in report
        assert "## Recommendations" in report
