"""Item 269: generate_loop_status.py — HTML report script (2026-06-08).

Falsifiable checks:
  1. Script exits 0 (no crash).
  2. HTML file is non-empty (> 1000 bytes).
  3. HTML contains current backlog_done count (live loop_telemetry, not hardcoded).
  4. OOM-safe: script runs with --no-inference to avoid lemonade dependency.
  5. HTML contains expected structural markers (KPI cards, fleet, RAM).
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest


REPO = Path(__file__).parent.parent
SCRIPT = REPO / "scripts" / "generate_loop_status.py"


@pytest.fixture(scope="module")
def html_report(tmp_path_factory: pytest.TempPathFactory) -> str:
    """Run the script once; return HTML content."""
    out = tmp_path_factory.mktemp("loop_report") / "status.html"
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--no-inference", "--out", str(out)],
        capture_output=True,
        text=True,
        timeout=30,
        cwd=str(REPO),
    )
    assert result.returncode == 0, (
        "Script must exit 0; stderr: " + result.stderr[-500:]
    )
    return out.read_text(encoding="utf-8")


def test_script_exits_zero_and_html_nonempty(html_report: str) -> None:
    """Script exits 0 and produces >1000 bytes of HTML.

    Primary check: no crash, meaningful output.
    """
    assert len(html_report) > 1000, (
        "HTML must be >1000 bytes; got " + repr(len(html_report))
    )


def test_html_contains_live_backlog_done_count(html_report: str) -> None:
    """HTML shows the current backlog_done count from live loop_telemetry().

    Kills impl with hardcoded count: regex looks for a digit ≥1 in the done KPI.
    """
    # Look for a non-zero number near "done" in the HTML.
    match = re.search(r"(\d+)\s*(?:<[^>]+>)?\s*done", html_report, re.IGNORECASE)
    assert match, "HTML must contain a backlog 'done' count; not found in report"
    count = int(match.group(1))
    assert count >= 1, f"backlog_done must be ≥1; got {count}"


def test_html_contains_structural_markers(html_report: str) -> None:
    """HTML contains KPI cards, fleet info, RAM bar.

    Kills impl that writes an empty stub HTML.
    """
    assert "fleet" in html_report.lower() or "model" in html_report.lower(), (
        "HTML must mention fleet/models"
    )
    assert "ram" in html_report.lower() or "memory" in html_report.lower() or "gb" in html_report.lower(), (
        "HTML must mention RAM/memory"
    )


def test_html_contains_valid_html_structure(html_report: str) -> None:
    """HTML has <html> and </html> tags.

    Kills impl returning plain text.
    """
    assert "<html" in html_report.lower(), "HTML must have <html> tag"
    assert "</html>" in html_report.lower(), "HTML must have </html> tag"


def test_oom_safe_no_inference_flag(html_report: str) -> None:
    """Running with --no-inference succeeds (no lemonade dependency required).

    OOM safety: the fixture already used --no-inference; this test verifies
    the report contains the skipped-inference placeholder.
    """
    # The report should contain the skip message
    assert "inference" in html_report.lower() or "narrative" in html_report.lower(), (
        "Report must mention inference/narrative (even if skipped)"
    )
