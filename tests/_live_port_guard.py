"""Blocking-suite guard: no unmarked test may reach the live inference router (:13305-13309).

THE DEFECT (2026-09-22): 258 tests in tests/{unit,inference,cache,compound} opened sockets to the
live lemonade router during the blocking gates. Most were read-only reachability probes whose
fallback made the test pass either way, so the verdict silently depended on fleet state. ~30 did
real WORK against the live fleet -- chat completions, model catalog fetches, and
``DELETE /active`` (tests/inference/test_dynamic_hotswapper.py unloaded the live model from
inside a unit test).

What this plugin does, for tests in the guarded dirs that are NOT marked ``integration``:

* Every connect to 127.0.0.1/localhost ports 13305-13309 is REFUSED (``ConnectionRefusedError``),
  i.e. the router is always "down" -- deterministic, and nothing reaches the live fleet.
* A refused attempt from a known read-only reachability probe (``PROBE_FUNCTIONS``, matched on
  the innermost ``src/cohezion`` frame) is tolerated: refusing it IS the offline fake.
* Any other attempt (a chat/embeddings/load/unload call, or a raw connect from test code) FAILS
  the test. Fix it with a fake; if the test genuinely asserts on a live service, mark it
  ``integration`` and list it in tests/unit/test_integration_marker_audit.py.

Collection-time probes (module-level ``skipif(not lemonade_reachable())`` for integration tests)
run outside any test and are not blocked, so ``-m integration`` still sees a live router.
Subprocesses are not covered (the patch is in-process).
"""

from __future__ import annotations

import socket
import threading
import traceback
from itertools import pairwise
from pathlib import Path
from typing import Any

import pytest


GUARDED_DIRS = frozenset({"unit", "inference", "cache", "compound"})
LIVE_PORTS = range(13305, 13310)
_LOCAL_HOSTS = frozenset({"127.0.0.1", "localhost", "::1", "0.0.0.0", "::ffff:127.0.0.1"})

# Read-only availability/catalog probes whose refusal is the intended offline behaviour.
# Matched against the innermost src/cohezion frame's function name at the connect site.
PROBE_FUNCTIONS = frozenset(
    {
        "is_available",  # cache/lemonade_encoder.py, inference/lemonade_embed_bridge.py
        "lemonade_available",  # compound/local_inference.py
        "_probe_lemonade",  # compound/cohezion_state.py
        "_count_models",
        "_list_flm_models",
        "_catalog_entry",  # compound/oom_guard.py
        "fetch_loaded_models",
        "resident_models_or_none",  # inference/hotswap.py
        "_catalog_sizes",
        "from_live_api",  # inference/model_card_harness.py (GET /v1/models)
    }
)


class _State:
    lock = threading.Lock()
    active: bool = False
    violations: list[str] = []


def _is_live_port(addr: Any) -> bool:
    try:
        return (
            isinstance(addr, tuple)
            and len(addr) >= 2
            and str(addr[0]) in _LOCAL_HOSTS
            and int(addr[1]) in LIVE_PORTS
        )
    except (TypeError, ValueError):
        return False


def _connect_site() -> str | None:
    """Innermost src/cohezion frame's function name, or None when the connect has no src caller."""
    for frame in reversed(traceback.extract_stack()[:-3]):
        if "/src/cohezion/" in frame.filename.replace("\\", "/"):
            return frame.name
    return None


def _check(addr: Any) -> None:
    if not (_State.active and _is_live_port(addr)):
        return
    site = _connect_site()
    if site not in PROBE_FUNCTIONS:
        with _State.lock:
            _State.violations.append(f"{addr[0]}:{addr[1]} from {site or 'test code'}")
    raise ConnectionRefusedError(111, f"live-port guard: {addr[0]}:{addr[1]} is off-limits")


_orig_connect = socket.socket.connect
_orig_connect_ex = socket.socket.connect_ex


def _guarded_connect(self: socket.socket, addr: Any) -> Any:
    _check(addr)
    return _orig_connect(self, addr)


def _guarded_connect_ex(self: socket.socket, addr: Any) -> int:
    try:
        _check(addr)
    except ConnectionRefusedError:
        return 111
    return _orig_connect_ex(self, addr)


def is_guarded(item: pytest.Item) -> bool:
    parts = Path(str(item.path)).parts
    in_dir = any(a == "tests" and b in GUARDED_DIRS for a, b in pairwise(parts))
    return in_dir and item.get_closest_marker("integration") is None


def pytest_configure(config: pytest.Config) -> None:
    socket.socket.connect = _guarded_connect  # type: ignore[method-assign]
    socket.socket.connect_ex = _guarded_connect_ex  # type: ignore[method-assign]


def pytest_unconfigure(config: pytest.Config) -> None:
    socket.socket.connect = _orig_connect  # type: ignore[method-assign]
    socket.socket.connect_ex = _orig_connect_ex  # type: ignore[method-assign]


def _raise_on_violations(item: pytest.Item, phase: str) -> None:
    with _State.lock:
        found, _State.violations = _State.violations, []
    if found:
        pytest.fail(
            f"{item.nodeid} ({phase}) tried to reach the live inference router: "
            + "; ".join(sorted(set(found)))
            + ". Fake the call, or mark the test integration (see tests/_live_port_guard.py).",
            pytrace=False,
        )


@pytest.hookimpl(wrapper=True)
def pytest_runtest_setup(item: pytest.Item):  # type: ignore[no-untyped-def]
    _State.active = is_guarded(item)
    _State.violations = []
    result = yield
    _raise_on_violations(item, "setup")
    return result


@pytest.hookimpl(wrapper=True)
def pytest_runtest_call(item: pytest.Item):  # type: ignore[no-untyped-def]
    result = yield
    _raise_on_violations(item, "call")
    return result


@pytest.hookimpl(wrapper=True)
def pytest_runtest_teardown(item: pytest.Item, nextitem: pytest.Item | None):  # type: ignore[no-untyped-def]
    try:
        result = yield
        _raise_on_violations(item, "teardown")
        return result
    finally:
        _State.active = False


def _live_url(url: object) -> bool:
    try:
        from urllib.parse import urlsplit

        parts = urlsplit(str(url))
        return (parts.hostname or "") in _LOCAL_HOSTS and parts.port in LIVE_PORTS
    except (TypeError, ValueError):
        return False


@pytest.fixture
def router_offline(monkeypatch: pytest.MonkeyPatch) -> None:
    """Explicit fake: the lemonade router is DOWN for this test.

    urllib and httpx requests to :13305-13309 raise their library's connection error before any
    socket is opened; everything else is untouched. Use it (``usefixtures``) for code under test
    whose fail-open "router unreachable" path is what the test exercises, instead of letting it
    discover that against the live fleet.
    """
    import urllib.error
    import urllib.request

    import httpx

    real_urlopen = urllib.request.urlopen

    def fake_urlopen(url, *args, **kwargs):  # type: ignore[no-untyped-def]
        target = url.full_url if isinstance(url, urllib.request.Request) else url
        if _live_url(target):
            raise urllib.error.URLError(ConnectionRefusedError(111, "router offline (test fake)"))
        return real_urlopen(url, *args, **kwargs)

    real_sync = httpx.HTTPTransport.handle_request
    real_async = httpx.AsyncHTTPTransport.handle_async_request

    def fake_sync(self, request):  # type: ignore[no-untyped-def]
        if _live_url(request.url):
            raise httpx.ConnectError("router offline (test fake)", request=request)
        return real_sync(self, request)

    async def fake_async(self, request):  # type: ignore[no-untyped-def]
        if _live_url(request.url):
            raise httpx.ConnectError("router offline (test fake)", request=request)
        return await real_async(self, request)

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", fake_sync)
    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", fake_async)
