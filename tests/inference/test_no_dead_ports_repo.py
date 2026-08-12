"""FT5 — repo-wide standing guard: no dead per-device inference ports in src/.

Invariant N1: the Lemonade OmniRouter on :13305 is the ONLY inference port. It
fronts the XDNA2 NPU, the RDNA3.5 iGPU and the CPU on demand over unified RAM.
The per-device servers :13306/:13307/:13308/:13309 are offline and redundant.

Why this is a STANDING test and not a one-off cleanup: the drift is silent and
expensive. On 2026-08-12 `inference/health.py` probed the four dead ports, so
`check_fleet()` reported every local lane DOWN on a healthy box, and
`fleet.route()` skipped each local candidate as "lane-down" and escalated toward
Ollama/cloud — inverting the local-first cost protocol and spending real money
for work the NPU/iGPU could do at $0. Nothing failed loudly; the fleet simply
looked dead.

Scanning technique matters. Use the AST and exclude docstrings:
  * a plain substring scan flags the very prose explaining why a port is avoided
  * a docstring IS an ``ast.Constant``, so it must be excluded explicitly
Three separate false positives were produced by unaudited scanners in one session
before this settled. See harness.md FT3.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest


DEAD_PORTS = (13306, 13307, 13308, 13309)
SRC = Path(__file__).resolve().parents[2] / "src" / "cohezion"

# Files permitted to name a dead port in EXECUTABLE code, each with a reason.
# Keep this as short as you can. Every entry is a place the fleet can silently lie.
# Only HISTORICAL RECORDS belong here — never live dispatch, probing or defaults.
ALLOWLIST: dict[str, str] = {
    "src/cohezion/flume/stealthskater_corpus.py": (
        "Stored record of a past experiment ('iGPU Lemonade server (13307) does not "
        "expose /v1/embeddings'). It documents what was actually observed at the time; "
        "rewriting the port would falsify the record. Not dispatch, not a probe."
    ),
}


def _python_files() -> list[Path]:
    return sorted(p for p in SRC.rglob("*.py") if "__pycache__" not in p.parts)


def _dead_port_hits(path: Path) -> list[str]:
    """Dead-port literals in executable code (docstrings and comments excluded)."""
    try:
        tree = ast.parse(path.read_text())
    except (SyntaxError, UnicodeDecodeError):
        return []

    docstring_ids = {
        id(node.value)
        for node in ast.walk(tree)
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant)
    }
    hits: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Constant):
            continue
        if id(node) in docstring_ids:
            continue
        if isinstance(node.value, int) and node.value in DEAD_PORTS:
            hits.append(f"int {node.value} (line {node.lineno})")
        elif isinstance(node.value, str):
            for p in DEAD_PORTS:
                if str(p) in node.value:
                    hits.append(f"str ':{p}' (line {node.lineno})")
    return hits


class TestNoDeadPortsRepoWide:
    def test_no_dead_inference_ports_in_src(self):
        offenders: dict[str, list[str]] = {}
        for path in _python_files():
            rel = str(path.relative_to(SRC.parent.parent))
            if rel in ALLOWLIST:
                continue
            hits = _dead_port_hits(path)
            if hits:
                offenders[rel] = hits

        assert not offenders, (
            "N1 violation — dead per-device inference ports in executable code.\n"
            "The OmniRouter :13305 fronts NPU/iGPU/CPU on demand; probing these "
            "reports the fleet down and forces cloud escalation.\n"
            + "\n".join(f"  {f}: {', '.join(h)}" for f, h in sorted(offenders.items()))
        )

    def test_scanner_actually_detects_a_violation(self, tmp_path):
        """The guard must be able to FAIL — a scanner that cannot fire is worse than none."""
        bad = tmp_path / "bad.py"
        bad.write_text('URL = "http://localhost:13307/v1/models"\nPORT = 13306\n')
        hits = _dead_port_hits(bad)
        assert len(hits) == 2, f"scanner missed a real violation: {hits}"

    @pytest.mark.parametrize(
        "source",
        [
            '"""Docstring mentioning :13306 to explain why it is avoided."""\nX = 1\n',
            "# comment mentioning 13307\nX = 1\n",
        ],
    )
    def test_scanner_does_not_flag_prose(self, tmp_path, source):
        """Prose explaining the dead ports must NOT trip the guard (the FT3 lesson)."""
        f = tmp_path / "prose.py"
        f.write_text(source)
        assert _dead_port_hits(f) == []
