"""H5 durable half: out-of-process execution must CONTAIN escapes the in-process allow-list cannot.

The discriminating pairs run the SAME escape two ways: in-process under ``safe_exec_globals``
(control — must succeed, proving the escape is real) and under ``run_untrusted`` (must be inert).
If the child's rlimits are neutralized, the ``run_untrusted`` half fails; the allow-list alone
does not make these tests pass.
"""

from __future__ import annotations

import time

import pytest

from cohezion.compound import sandboxed_exec
from cohezion.compound.safe_exec import safe_exec_globals
from cohezion.compound.sandboxed_exec import run_untrusted


ESCAPE_SYSTEM = "import collections\ncollections._sys.modules['os'].system('touch {marker}')\n"
ESCAPE_READ = (
    "import collections\n"
    "os = collections._sys.modules['os']\n"
    "fd = os.open({path!r}, os.O_RDONLY)\n"
    "leak = os.read(fd, 100).decode()\n"
)


# --- the escapes are real (controls) ---------------------------------------------------------


def test_control_in_process_allowlist_does_not_stop_system_escape(tmp_path):
    marker = tmp_path / "pwned_in_process"
    exec(ESCAPE_SYSTEM.format(marker=marker), safe_exec_globals())  # noqa: S102
    assert marker.exists(), "control broken: escape no longer works in-process"


# --- discriminating: the boundary makes them inert ---------------------------------------------


def test_system_escape_cannot_spawn_a_process(tmp_path):
    marker = tmp_path / "pwned_sandboxed"
    r = run_untrusted(ESCAPE_SYSTEM.format(marker=marker) + "rc = 1\n", collect=True)
    assert not marker.exists()
    assert r.isolation in {"rlimit", "bwrap+rlimit"}


def test_file_read_escape_is_blocked(tmp_path):
    secret = tmp_path / "secret.txt"
    secret.write_text("TOPSECRET")
    r = run_untrusted(ESCAPE_READ.format(path=str(secret)), collect=True)
    assert "TOPSECRET" not in repr(r)
    assert not r.ok


def test_socket_escape_is_blocked():
    # Via importlib so the escape does not depend on _socket already being in sys.modules —
    # an earlier sys.modules['_socket'] version failed with KeyError and survived the mutant.
    code = (
        "import collections\n"
        "socket = collections._sys.modules['importlib'].import_module('socket')\n"
        "s = socket.socket()\n"
        "made = True\n"
    )
    r = run_untrusted(code, collect=True)
    assert not r.ok
    assert "KeyError" not in r.error and "NameError" not in r.error, r.error


def test_parent_environment_secrets_are_not_inherited(monkeypatch):
    monkeypatch.setenv("CZ_TEST_SECRET_TOKEN", "hunter2")
    code = "import collections\nenv = dict(collections._sys.modules['os'].environ)\n"
    r = run_untrusted(code, collect=True)
    assert r.ok, r.error
    assert "hunter2" not in repr(r.value)


def test_cpu_loop_is_killed_near_the_timeout():
    start = time.monotonic()
    r = run_untrusted("while True:\n    pass\n", collect=True, timeout_s=2)
    assert not r.ok
    assert time.monotonic() - start < 12


def test_wall_clock_sleep_is_killed_even_without_cpu_use():
    code = "import collections\ncollections._sys.modules['time'].sleep(60)\n"
    start = time.monotonic()
    r = run_untrusted(code, collect=True, timeout_s=1)
    assert not r.ok and r.error == "timeout"
    assert time.monotonic() - start < 10


def test_memory_bomb_fails_instead_of_allocating():
    r = run_untrusted("x = bytearray(8 * 1024 ** 3)\n", collect=True, mem_mb=512)
    assert not r.ok
    assert "MemoryError" in r.error


def test_output_flood_is_capped():
    code = "import collections\nos = collections._sys.modules['os']\nwhile True:\n    os.write(1, b'A' * 65536)\n"
    r = run_untrusted(code, collect=True, timeout_s=5)
    assert not r.ok


# --- fail closed --------------------------------------------------------------------------------


def test_spawn_failure_fails_closed_without_in_process_fallback(tmp_path, monkeypatch):
    monkeypatch.setattr(sandboxed_exec, "_python_exec", lambda: str(tmp_path / "no-such-python"))
    monkeypatch.setattr(sandboxed_exec, "_bwrap_prefix", lambda: ())
    marker = tmp_path / "ran_in_parent"
    r = run_untrusted(ESCAPE_SYSTEM.format(marker=marker), collect=True)
    assert not r.ok and "sandbox refused" in r.error
    assert not marker.exists()


# --- availability: legit solver code still works ------------------------------------------------


def test_call_returns_json_value_for_numpy_solver():
    code = "import numpy as np\ndef solve(grid):\n    return np.flipud(np.array(grid)).tolist()\n"
    r = run_untrusted(code, call="solve", args=[[[1, 2], [3, 4]]])
    assert r.ok, r.error
    assert r.value == [[3, 4], [1, 2]]


def test_undefined_entry_point_is_an_error_not_none():
    r = run_untrusted("x = 1\n", call="solve", args=[[]])
    assert not r.ok and "solve" in r.error


def test_sympy_bindings_and_collect():
    code = "x = symbols('x')\nroots = solve(Eq(x**2, 4), x)\nn = isprime(97)\n"
    bindings = {
        "symbols": "sympy:symbols",
        "solve": "sympy:solve",
        "Eq": "sympy:Eq",
        "isprime": "sympy:isprime",
    }
    r = run_untrusted(code, collect=True, bindings=bindings)
    assert r.ok, r.error
    assert r.value["n"] is True
    assert sorted(r.value["roots"]) == [-2.0, 2.0]


def test_print_is_captured_not_mistaken_for_result():
    r = run_untrusted("print('{\"ok\": false}')\nv = 3\n", collect=True)
    assert r.ok and r.value == {"v": 3}
    assert "ok" in r.stdout


def test_class_defs_flag_allows_class_statements():
    code = (
        "class Env:\n    def step(self):\n        return 7\n\ndef run():\n    return Env().step()\n"
    )
    assert not run_untrusted(code, call="run").ok
    r = run_untrusted(code, call="run", class_defs=True)
    assert r.ok and r.value == 7


@pytest.mark.parametrize("snippet", ["import os\n", "open('/etc/hostname').read()\n"])
def test_in_process_gate_still_applies_inside_child(snippet):
    assert not run_untrusted(snippet, collect=True).ok


# --- consumer: SymbolicExecutor (was in-process exec, H5 site) --------------------------------


def test_symbolic_executor_escape_is_contained(tmp_path):
    from cohezion.compound.symbolic_executor import SymbolicExecutor

    marker = tmp_path / "pwned_symbolic"
    res = SymbolicExecutor().execute(ESCAPE_SYSTEM.format(marker=marker))
    # The escape reaches os.system but the fork fails (returns -1): code "succeeds", no process ran.
    assert res["success"] is True
    assert not marker.exists()


def test_symbolic_executor_lazy_sympy_paths_still_work():
    """Oracle-checked against the pre-port in-process executor (integrate lazily imports
    stdlib `dataclasses`, which failed under NOFILE=3 until stdlib sources were preloaded)."""
    from cohezion.compound.symbolic_executor import SymbolicExecutor

    ex = SymbolicExecutor()
    assert (
        ex.execute("x = symbols('x')\nresult = integrate(x**2, (x, 0, 3))\n")["results"]["result"]
        == 9
    )
    solved = ex.execute_command("SOLVE(x**2 = 4, x)")
    assert solved["success"] and sorted(solved["results"]["result"]) == [-2, 2]
    failed = ex.execute("result = 1/0\n")
    assert not failed["success"] and "ZeroDivisionError" in failed["traceback"]
