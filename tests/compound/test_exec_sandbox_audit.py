"""Discriminating tests for the executor↔sandbox coverage audit (item 48, 2026-06-06).

`unsandboxed_exec_paths(paths)` flags dynamic-code-execution sinks (exec/eval/subprocess.*/os.system)
that are NOT lexically inside an IsolationContext `with`-block. Report-only — a real finding becomes
a separate permission-gated remediation. Prompted by langchain.com "agents run untrusted code by
definition" (the principle, not its cloud-microVM product).

Each test fails a plausible wrong impl:
  - misses an unsandboxed exec → test_unsandboxed_exec_flagged,
  - treats ANY with-block as sandboxed (e.g. `with open()`) → test_non_isolation_with_still_flagged,
  - flags an exec that IS inside IsolationContext → test_isolation_with_is_clean,
  - flags a file with no exec sink → test_no_sink_out_of_scope.
"""

from __future__ import annotations

from pathlib import Path

from cohezion.compound.exec_sandbox_audit import unsandboxed_exec_paths


def _sinks(rows) -> set[str]:
    return {r.sink for r in rows}


def test_unsandboxed_exec_flagged(tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text("def run_it(code):\n    exec(code)\n")
    rows = unsandboxed_exec_paths([tmp_path])
    assert len(rows) == 1
    assert rows[0].sink == "exec"
    assert rows[0].location.endswith(":2")  # file:line precision
    assert rows[0].sandboxed is False


def test_isolation_with_is_clean(tmp_path: Path) -> None:
    (tmp_path / "b.py").write_text(
        "def run_it(code):\n    with IsolationContext() as ctx:\n        exec(code)\n"
    )
    assert unsandboxed_exec_paths([tmp_path]) == []  # exec is inside isolation → not flagged


def test_non_isolation_with_still_flagged(tmp_path: Path) -> None:
    # A plain `with open()` is NOT isolation — the exec inside it must still be flagged.
    (tmp_path / "c.py").write_text("def w(code):\n    with open('x') as f:\n        exec(code)\n")
    rows = unsandboxed_exec_paths([tmp_path])
    assert len(rows) == 1 and rows[0].sink == "exec"


def test_subprocess_and_os_system_flagged(tmp_path: Path) -> None:
    (tmp_path / "d.py").write_text(
        "import subprocess, os\ndef sh(cmd):\n    subprocess.run(cmd)\n    os.system(cmd)\n"
    )
    rows = unsandboxed_exec_paths([tmp_path])
    assert _sinks(rows) == {"subprocess.run", "os.system"}


def test_no_sink_out_of_scope(tmp_path: Path) -> None:
    (tmp_path / "e.py").write_text("def pure(x):\n    return x + 1\n")
    assert unsandboxed_exec_paths([tmp_path]) == []


def test_eval_inside_isolation_clean_but_outside_flagged(tmp_path: Path) -> None:
    (tmp_path / "f.py").write_text(
        "def two(code):\n"
        "    eval(code)\n"  # line 2 — outside isolation → flagged
        "    with IsolationContext():\n"
        "        eval(code)\n"  # line 4 — inside isolation → clean
    )
    rows = unsandboxed_exec_paths([tmp_path])
    assert len(rows) == 1
    assert rows[0].location.endswith(":2")
