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
