"""Discriminating tests for sandboxing.executor backend selection (V-model audit, 2026-06-05).

`sandboxing` was a no-test module. SandboxManager._get_backend is the pure selection logic
(backend constructors are cheap — Docker/Firecracker I/O is deferred to async _ensure_image).
Each test fails a plausible wrong impl:
  - selection that returns the wrong backend class,
  - a cache that re-constructs the backend on every call,
  - the security-relevant ResourceLimits default flipping network ON.

FINDING (pin-actual, minor): `preferred_backend` is typed Literal[...,"gvisor"], but _get_backend
handles only docker/firecracker and raises ValueError on gvisor — a type-allowed-but-unhandled
value. Pinned by test_gvisor_is_type_allowed_but_unhandled.
"""

from __future__ import annotations

from cohezion.sandboxing.executor import (
    DockerSandbox,
    FirecrackerSandbox,
    ResourceLimits,
    SandboxManager,
)


def test_docker_is_default_backend() -> None:
    assert isinstance(SandboxManager()._get_backend(), DockerSandbox)


def test_firecracker_selection() -> None:
    assert isinstance(
        SandboxManager(preferred_backend="firecracker")._get_backend(), FirecrackerSandbox
    )


def test_backend_is_cached_not_reconstructed() -> None:
    # Discriminates an impl that builds a fresh backend each call (would break warm state /
    # _initialized tracking). Same object on repeated calls.
    mgr = SandboxManager()
    assert mgr._get_backend() is mgr._get_backend()


def test_gvisor_is_type_allowed_but_unhandled() -> None:
    # pin-actual: gvisor is in the Literal type but _get_backend has no branch -> ValueError.
    import pytest

    with pytest.raises(ValueError, match="gvisor"):
        SandboxManager(preferred_backend="gvisor")._get_backend()  # type: ignore[arg-type]


def test_resource_limits_default_network_is_off() -> None:
    # Security-relevant default: sandboxed code must default to NO network.
    lim = ResourceLimits()
    assert lim.network is False
    assert lim.timeout_seconds == 300 and lim.pids_limit == 100


# ── Timeout actually stops the container (2026-11-04) ─────────────────────────────────────────
class _FakeProc:
    def __init__(self, *, hang: bool) -> None:
        self.hang = hang
        self.returncode: int | None = None if hang else 0
        self.killed = False

    async def communicate(self):
        import asyncio

        if self.hang:
            await asyncio.sleep(3600)
        return b"", b""

    async def wait(self) -> int:
        if self.returncode is None:
            self.returncode = -9
        return self.returncode

    def kill(self) -> None:
        self.killed = True
        self.returncode = -9


def _run_with_fake_docker(monkeypatch, *, hang: bool):
    import asyncio

    import cohezion.sandboxing.executor as ex

    calls: list[tuple[str, ...]] = []
    procs: list[_FakeProc] = []

    async def fake_exec(*argv, **_kw):
        calls.append(argv)
        proc = _FakeProc(hang=hang and argv[1] == "run")
        procs.append(proc)
        return proc

    monkeypatch.setattr(ex.asyncio, "create_subprocess_exec", fake_exec)
    sandbox = DockerSandbox()
    sandbox._initialized = True  # skip the image pull
    limits = ResourceLimits(timeout_seconds=0.05)  # type: ignore[arg-type]
    # Outer guard: an implementation whose timeout never fires fails here instead of hanging.
    result = asyncio.run(
        asyncio.wait_for(sandbox.execute("while True: pass", limits=limits), timeout=5)
    )
    return result, calls, procs


def test_timeout_kills_the_container_it_started(monkeypatch) -> None:
    """Discriminating: the old code passed "$(docker ps ...)" as a literal argv element (no shell,
    so no substitution) and only timed out the spawn, so a hung container ran on."""
    result, calls, procs = _run_with_fake_docker(monkeypatch, hang=True)

    assert result.success is False and "Timeout" in result.stderr
    run_argv = calls[0]
    name = run_argv[run_argv.index("--name") + 1]
    assert ("docker", "kill", name) in calls, calls
    assert not any("$(" in arg for argv in calls for arg in argv)
    assert procs[0].killed, "the docker client process was not reaped"


def test_fast_run_is_not_killed(monkeypatch) -> None:
    result, calls, _ = _run_with_fake_docker(monkeypatch, hang=False)
    assert result.success is True
    assert not any(argv[:2] == ("docker", "kill") for argv in calls)
