"""Tests for LocalImprovementExecutor AutoHarness syntax guard and model selection.

Verifies:
- Syntactically invalid Python patches are rejected before writing (AutoHarness gate)
- Valid patches are written normally
- Inline harness command is extracted from model response
- Omni-first model selection (quality over speed)
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch


def _make_executor(tmp_path):
    """Build a LocalImprovementExecutor with a mocked Lemonade server check."""
    from cohezion.compound.autonomous_loop.coordinator import LoopConfig
    from cohezion.compound.autonomous_loop.local_executor import LocalImprovementExecutor

    config = LoopConfig(local_base_url="http://localhost:19999")
    with patch.object(LocalImprovementExecutor, "_check_server"):
        exec_ = LocalImprovementExecutor(config)
    exec_._available_models = [
        "Qwen3.6-35B-A3B-MTP-GGUF",
        "Gemma-4-E4B-it-GGUF",
    ]
    exec_._started = True
    exec_._worktree_path = str(tmp_path)
    return exec_


class TestAutoHarnessSyntaxGuard:
    def test_valid_python_patch_is_written(self, tmp_path: Path) -> None:
        exec_ = _make_executor(tmp_path)
        content = "x = 1\nprint(x)\n"
        response = f"=== FILE: test_mod.py ===\n{content}=== END FILE ==="
        ok, errors = exec_._apply_suggestions(response, str(tmp_path))
        assert ok is True
        assert errors == []
        assert (tmp_path / "test_mod.py").read_text() == content

    def test_invalid_python_patch_is_rejected(self, tmp_path: Path) -> None:
        exec_ = _make_executor(tmp_path)
        bad_content = "def foo(\n    # missing closing paren\n"
        response = f"=== FILE: bad_mod.py ===\n{bad_content}=== END FILE ==="
        ok, errors = exec_._apply_suggestions(response, str(tmp_path))
        assert ok is False
        assert len(errors) == 1
        assert "Syntax error" in errors[0]
        # File must NOT be written
        assert not (tmp_path / "bad_mod.py").exists()

    def test_non_python_file_skips_syntax_check(self, tmp_path: Path) -> None:
        exec_ = _make_executor(tmp_path)
        content = "not valid python {{ }"
        response = f"=== FILE: config.yaml ===\n{content}=== END FILE ==="
        ok, errors = exec_._apply_suggestions(response, str(tmp_path))
        assert ok is True
        assert (tmp_path / "config.yaml").read_text() == content

    def test_partial_rejection_continues_valid_patches(self, tmp_path: Path) -> None:
        """A syntax error in one patch shouldn't block other valid patches."""
        exec_ = _make_executor(tmp_path)
        bad = "def bad(\n"
        good = "x = 42\n"
        response = (
            f"=== FILE: bad.py ===\n{bad}=== END FILE ===\n"
            f"=== FILE: good.py ===\n{good}=== END FILE ==="
        )
        ok, errors = exec_._apply_suggestions(response, str(tmp_path))
        assert ok is False  # overall: one error
        assert len(errors) == 1
        assert not (tmp_path / "bad.py").exists()
        assert (tmp_path / "good.py").read_text() == good

    def test_no_file_blocks_returns_ok(self, tmp_path: Path) -> None:
        exec_ = _make_executor(tmp_path)
        ok, errors = exec_._apply_suggestions("no file blocks here", str(tmp_path))
        assert ok is True
        assert errors == []


class TestHarnessExtraction:
    def test_extracts_harness_command(self, tmp_path: Path) -> None:
        exec_ = _make_executor(tmp_path)
        response = (
            "Some text\n=== HARNESS: python -c 'import mymod; print(mymod.fn())' ===\nMore text"
        )
        cmd = exec_._extract_harness_cmd(response)
        assert cmd == "python -c 'import mymod; print(mymod.fn())'"

    def test_no_harness_returns_empty(self, tmp_path: Path) -> None:
        exec_ = _make_executor(tmp_path)
        cmd = exec_._extract_harness_cmd("no harness block here")
        assert cmd == ""


class TestModelSelection:
    def test_prefers_omni_planner_model(self, tmp_path: Path) -> None:
        from cohezion.compound.autonomous_loop.local_executor import OMNI_PLANNER_MODEL

        exec_ = _make_executor(tmp_path)
        exec_._model = OMNI_PLANNER_MODEL
        exec_._available_models = [OMNI_PLANNER_MODEL, "Gemma-4-E4B-it-GGUF"]
        assert exec_._select_model() == OMNI_PLANNER_MODEL

    def test_falls_back_to_gemma_when_omni_unavailable(self, tmp_path: Path) -> None:
        from cohezion.compound.autonomous_loop.local_executor import OMNI_PLANNER_MODEL

        exec_ = _make_executor(tmp_path)
        exec_._model = OMNI_PLANNER_MODEL
        exec_._available_models = ["Gemma-4-E4B-it-GGUF"]
        assert exec_._select_model() == "Gemma-4-E4B-it-GGUF"

    def test_never_silently_downgrades_to_unknown_small_model(self, tmp_path: Path) -> None:
        """When neither Omni nor Gemma-4-E4B is available, use configured model (not a random one)."""
        from cohezion.compound.autonomous_loop.local_executor import OMNI_PLANNER_MODEL

        exec_ = _make_executor(tmp_path)
        exec_._model = OMNI_PLANNER_MODEL
        exec_._available_models = ["some-tiny-unknown-model"]
        # Should return the configured model (last-resort), not the tiny unknown one
        assert exec_._select_model() == OMNI_PLANNER_MODEL
