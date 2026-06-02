"""Regression test for the Mellum-2 GGUF watcher's SurrealDB bus-log auth.

The watcher silently failed to persist detections with HTTP 403 because BUS_HEADERS
omitted the Authorization header. This discriminating test would FAIL the prior
(no-auth) implementation: it asserts the header is present AND decodes to the
expected root:root dev credentials, plus the ns/db routing headers per the
research-defaults SurrealDB HTTP pattern.
"""

from __future__ import annotations

import base64
import importlib.util
from pathlib import Path

import pytest

_WATCHER = Path(__file__).resolve().parents[2] / "scripts" / "experiments" / "watch_mellum2_gguf.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("watch_mellum2_gguf", _WATCHER)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.mark.unit
def test_bus_headers_carry_root_auth_and_routing() -> None:
    mod = _load_module()
    h = mod.BUS_HEADERS
    # routing headers (per research-defaults SurrealDB HTTP pattern)
    assert h["surreal-ns"] == "cohezion"
    assert h["surreal-db"] == "main"
    # the bug fix: Basic auth must be present and decode to root:root
    auth = h.get("Authorization", "")
    assert auth.startswith("Basic "), "missing Basic auth -> SurrealDB returns 403"
    decoded = base64.b64decode(auth.split(" ", 1)[1]).decode("ascii")
    assert decoded == "root:root"
