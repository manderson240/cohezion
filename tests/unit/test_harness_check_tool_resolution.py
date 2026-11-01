"""harness_check must resolve ruff/mypy/uv from the repo venv, not a bare PATH lookup."""

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def _load():
    spec = importlib.util.spec_from_file_location(
        "harness_check_under_test", ROOT / ".claude" / "rules" / "harness_check.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_resolves_from_venv_bin_when_present(tmp_path, monkeypatch):
    mod = _load()
    fake_bin = tmp_path / ".venv" / "bin"
    fake_bin.mkdir(parents=True)
    (fake_bin / "ruff").write_text("#!/bin/sh\n")
    monkeypatch.setattr(mod, "PROJECT_ROOT", tmp_path)
    assert mod._resolve_tool(["ruff", "format", "--check"]) == [
        str(fake_bin / "ruff"),
        "format",
        "--check",
    ]


def test_unknown_tool_left_untouched(tmp_path, monkeypatch):
    mod = _load()
    monkeypatch.setattr(mod, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(mod.Path, "home", classmethod(lambda cls: tmp_path))
    assert mod._resolve_tool(["no-such-tool-xyz", "a"]) == ["no-such-tool-xyz", "a"]


def test_run_check_executes_the_resolved_path(tmp_path, monkeypatch):
    mod = _load()
    fake_bin = tmp_path / ".venv" / "bin"
    fake_bin.mkdir(parents=True)
    (fake_bin / "ruff").write_text("#!/bin/sh\n")
    monkeypatch.setattr(mod, "PROJECT_ROOT", tmp_path)
    seen = []

    def fake_run(cmd, **kwargs):
        seen.append(cmd)
        return mod.subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr(mod.subprocess, "run", fake_run)
    mod.run_check("format", {"cmd": ["ruff", "format"], "desc": "d", "timeout": 1}, ["a.py"])
    assert seen == [[str(fake_bin / "ruff"), "format", "a.py"]]
