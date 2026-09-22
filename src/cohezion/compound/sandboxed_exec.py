"""Out-of-process execution of untrusted / LLM-generated Python (security finding H5, durable half).

``safe_exec.safe_exec_globals`` restricts builtins but, by its own docstring, is NOT a boundary:
``collections._sys.modules['os'].system(...)`` and ``__subclasses__`` gadget chains escape it.
``run_untrusted`` runs the code in a separate interpreter whose kernel resource limits make those
escapes inert even when they reach ``os``:

  * RLIMIT_NPROC=0  -> fork / os.system / subprocess fail (no shell, no exec of binaries)
  * RLIMIT_NOFILE=3 -> open() and socket() fail (no file reads, no network)
  * RLIMIT_FSIZE=0, RLIMIT_AS, RLIMIT_CPU + a parent-side wall-clock kill of the process group
  * allow-listed environment (no inherited secrets), throwaway cwd, ``python -I``
  * outer ``bwrap --unshare-all`` layer when user namespaces are available (probed at runtime)

Measured limits of the rlimit-only floor (no namespaces): the child can still send signals to
same-UID processes (``kill``) and use already-open fds 0-2. ``bwrap --unshare-pid`` closes the
signal path; ``SandboxResult.isolation`` reports which layer actually ran, so callers can tell.

FAIL CLOSED: if the child cannot be spawned, a limit cannot be applied, or the output is
unparseable, the result is ``ok=False`` — there is NO fallback to in-process ``exec``. The cost
is explicit: on a box that refuses subprocesses, LLM solvers return no answer instead of running
unconfined. That is the intended trade for a prompt-injection -> RCE chain.

Values cross the boundary as JSON only. Never unpickle child output.

CONTRACT — what the rlimit floor does and does NOT contain (measured, not assumed):
  * The rlimit-only floor (bwrap absent or userns denied) is an AVAILABILITY limit plus a speed
    bump, NOT a filesystem boundary. NOFILE=3 stops open()/socket(), but PATH-BASED mutation needs
    no fd: ``os.mkdir/rename/unlink/symlink/rmdir`` through a reachable ``os`` module succeed at
    absolute paths within the child's UID. On a host without bwrap/userns, untrusted code can
    write/delete files that UID can. ``bwrap --ro-bind / /`` (``isolation == "bwrap+rlimit"``) is
    the filesystem boundary; check ``SandboxResult.isolation``.
  * Other documented gaps: same-UID signals and already-open fds 0-2.
  * RESULTS PRODUCED AFTER UNTRUSTED CODE HAS EXECUTED ARE UNTRUSTED DATA. The code shares the
    child process with the result writer and can ``os.write(1, forged_json); os._exit(0)``, so
    ``ok``/``value``/``error``/``stdout``/``traceback`` may be attacker-chosen (including the text
    "sandbox refused" or "timeout"). No nonce or extra fd can fix this (the code can reach both).
    Fail-closed guarantees hold only for PRE-EXECUTION failures (spawn, rlimit, unloadable child):
    ``SandboxResult.stage == "pre-exec"``. Anything with ``stage == "post-exec"`` must be validated
    by the consumer (type, shape, size) before use. The stage is derived from a marker the child
    writes before running user code, so forged output cannot make itself look pre-exec.
"""

from __future__ import annotations

import contextlib
import functools
import json
import os
import selectors
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any


_HERE = Path(__file__).resolve().parent
_CHILD = _HERE / "_sandbox_child.py"
_SAFE_EXEC = _HERE / "safe_exec.py"
_MAX_OUTPUT_BYTES = 4 * 1024 * 1024
_ENV_ALLOW = ("LANG", "LC_ALL", "TZ")


@dataclass(frozen=True)
class SandboxResult:
    ok: bool
    value: Any = None
    error: str = ""
    stdout: str = ""
    traceback: str = ""
    isolation: str = "none"  # "bwrap+rlimit" | "rlimit" | "none" (never started)
    stage: str = "pre-exec"  # "pre-exec" (trusted refusal) | "post-exec" (UNTRUSTED data)


def is_plain_json(value: Any, *, max_nodes: int = 100_000) -> bool:
    """True iff ``value`` is a bounded tree of None/bool/int/float/str/list/dict[str,...]."""
    stack, seen = [value], 0
    while stack:
        v = stack.pop()
        seen += 1
        if seen > max_nodes:
            return False
        if v is None or isinstance(v, (bool, int, float, str)):
            continue
        if isinstance(v, list):
            stack.extend(v)
        elif isinstance(v, dict):
            if not all(isinstance(k, str) for k in v):
                return False
            stack.extend(v.values())
        else:
            return False
    return True


def _python_exec() -> str:
    """Repo venv interpreter (coding-standards L367), falling back to the running one."""
    venv_py = _HERE.parents[2] / ".venv" / "bin" / "python3"
    return str(venv_py) if venv_py.exists() else sys.executable


@functools.cache
def _bwrap_prefix() -> tuple[str, ...]:
    """Namespace isolation prefix if bwrap can create namespaces HERE, else empty.

    Probed live rather than assumed: bwrap is installed on hosts where unprivileged user
    namespaces are denied (e.g. inside an agent sandbox), and that denial says nothing about
    other hosts. The ro-bind of / is required because the child reads the venv interpreter.
    """
    bwrap = shutil.which("bwrap")
    if not bwrap:
        return ()
    prefix = (
        bwrap, "--ro-bind", "/", "/", "--dev", "/dev", "--proc", "/proc", "--tmpfs", "/tmp",
        "--unshare-all", "--die-with-parent", "--new-session", "--chdir", "/tmp",
    )  # fmt: skip
    try:
        probe = subprocess.run([*prefix, "true"], capture_output=True, timeout=5, check=False)
    except (OSError, subprocess.SubprocessError):
        return ()
    return prefix if probe.returncode == 0 else ()


def bwrap_prefix() -> tuple[str, ...]:
    """Public view of the live namespace probe (``()`` when bwrap cannot isolate here).

    Reused by ``act_loop.run_tests``, which cannot use :func:`run_untrusted` itself: pytest
    needs more than NOFILE=3/NPROC=0. Callers append their own binds and ``--chdir``.
    """
    return _bwrap_prefix()


def _kill_group(proc: subprocess.Popen) -> None:
    with contextlib.suppress(ProcessLookupError, PermissionError):
        os.killpg(proc.pid, signal.SIGKILL)
    proc.wait()


def _read_bounded(proc: subprocess.Popen, deadline: float) -> tuple[bytes, str]:
    """Read child stdout until EOF, the wall-clock deadline, or the byte cap (both kill)."""
    stdout = proc.stdout
    if stdout is None:
        return b"", "child stdout not captured"
    chunks: list[bytes] = []
    total = 0
    with selectors.DefaultSelector() as sel:
        sel.register(stdout, selectors.EVENT_READ)
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                _kill_group(proc)
                return b"".join(chunks), "timeout"
            if not sel.select(timeout=remaining):
                continue
            chunk = os.read(stdout.fileno(), 65536)
            if not chunk:
                return b"".join(chunks), ""
            chunks.append(chunk)
            total += len(chunk)
            if total > _MAX_OUTPUT_BYTES:
                _kill_group(proc)
                return b"".join(chunks), "output exceeded cap"


def run_untrusted(
    code: str,
    *,
    call: str | None = None,
    args: tuple | list = (),
    collect: bool = False,
    bindings: dict[str, str] | None = None,
    timeout_s: float = 10.0,
    mem_mb: int = 2048,
) -> SandboxResult:
    """Execute ``code`` out of process under kernel resource limits.

    call:     name of a function the code defines; it is invoked with JSON ``args`` and its
              JSON-coerced return value becomes ``value``.
    collect:  instead, return the code's non-underscore, non-callable top-level variables.
    bindings: names to pre-bind, as ``"module"`` or ``"module:attr"`` (e.g. ``{"np": "numpy"}``)
              — objects cannot cross a process boundary, so the child imports them itself.
    """
    payload = json.dumps(
        {
            "code": code,
            "call": call,
            "args": list(args),
            "collect": collect,
            "bindings": bindings or {},
            "cpu_s": max(1, int(timeout_s) + 1),
            "mem_bytes": mem_mb * 1024 * 1024,
        }
    ).encode()
    prefix = _bwrap_prefix()
    isolation = "bwrap+rlimit" if prefix else "rlimit"
    env = {k: os.environ[k] for k in _ENV_ALLOW if k in os.environ}
    env.update(PATH="/usr/bin:/bin", OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="1")
    cmd = [*prefix, _python_exec(), "-I", str(_CHILD), str(_SAFE_EXEC)]

    with tempfile.TemporaryDirectory(prefix="cz_untrusted_") as cwd:
        try:
            proc = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                cwd=cwd,
                env=env,
                start_new_session=True,
            )
        except OSError as exc:
            return SandboxResult(ok=False, error=f"sandbox refused: spawn failed ({exc})")
        if proc.stdin is None or proc.stdout is None:  # both are PIPE; unreachable in practice
            _kill_group(proc)
            return SandboxResult(ok=False, error="sandbox refused: child pipes missing")
        deadline = time.monotonic() + timeout_s + 5.0  # + interpreter/numpy startup
        with contextlib.suppress(BrokenPipeError):
            proc.stdin.write(payload)
            proc.stdin.close()
        out, failure = _read_bounded(proc, deadline)
        proc.stdout.close()
        lines = out.decode(errors="replace").strip().splitlines()
        # The child writes {"armed": true} as its FIRST line, before user code runs. Its presence
        # (not any later content) is what makes everything else post-exec / untrusted.
        armed = _is_armed(lines[0]) if lines else False
        stage = "post-exec" if armed else "pre-exec"
        if failure:
            return SandboxResult(ok=False, error=failure, isolation=isolation, stage=stage)
        rc = proc.wait()

    result_lines = lines[1:] if armed else lines
    try:
        data = json.loads(result_lines[-1])
        if not isinstance(data, dict):
            raise ValueError("result is not an object")
    except (IndexError, ValueError):
        return SandboxResult(
            ok=False, error=f"no result from child (rc={rc})", isolation=isolation, stage=stage
        )
    return SandboxResult(
        ok=bool(data.get("ok")),
        value=data.get("value"),
        error=str(data.get("error", "")),
        stdout=str(data.get("stdout", "")),
        traceback=str(data.get("traceback", "")),
        isolation=isolation,
        stage=stage,
    )


def _is_armed(line: str) -> bool:
    try:
        return bool(json.loads(line) == {"armed": True})
    except ValueError:
        return False
