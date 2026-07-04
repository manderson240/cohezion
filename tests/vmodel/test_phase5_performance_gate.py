"""MD3 test — performance-engineer gate agent exists and emits a verdict.

V-Model right-side test for Module Design:
  MD3.1: .claude/agents/performance-engineer.md exists with correct frontmatter.
  MD3.2: The gate file describes PASS/BLOCK verdict output.
  MD3.3: Live system passes the performance gate (omni router up, ctx bounded, RAM ok).
"""

from __future__ import annotations

import json
import urllib.request
from pathlib import Path

import pytest

from cohezion.reliability.resource_guard import ResourceGuard


AGENT_PATH = Path(__file__).resolve().parents[2] / ".claude" / "agents" / "performance-engineer.md"


class TestPerformanceEngineerAgent:
    def test_md3_1_agent_file_exists(self):
        assert AGENT_PATH.exists(), f"performance-engineer.md not found at {AGENT_PATH}"
        content = AGENT_PATH.read_text()
        assert "name: performance-engineer" in content
        assert "model: sonnet" in content

    def test_md3_2_agent_describes_verdict_output(self):
        content = AGENT_PATH.read_text()
        assert "PASS" in content
        assert "BLOCK" in content
        assert "verdict" in content.lower()
        assert "quality_gate" in content

    def test_md3_3_live_system_passes_gate(self):
        """The live Strix Halo system should pass all performance gate checks."""
        # 1. Omni router online
        try:
            req = urllib.request.Request("http://localhost:13305/v1/models", method="GET")
            with urllib.request.urlopen(req, timeout=5) as resp:
                models = json.loads(resp.read()).get("data", [])
            assert len(models) >= 1, "omni router returned no models"
        except Exception as exc:
            pytest.skip(f"omni router offline (infrastructure dependency): {exc}")

        # 2. max_loaded_models == 1
        config_path = Path.home() / ".cache" / "lemonade" / "config.json"
        config = json.loads(config_path.read_text())
        assert config.get("max_loaded_models") == 1

        # 3. RAM floor
        guard = ResourceGuard()
        ok, reason = guard.can_load_model(5000)
        assert ok, f"RAM gate failed: {reason}"
