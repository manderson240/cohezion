"""Un-mocked stdio handshake tests for the cohezion-bridge MCP server.

These drive the REAL process over stdin/stdout, because the defect they guard
against is invisible to any test that imports the module and calls a method:
the desktop client rejected `initialize` with

    Invalid result for initialize: path ["protocolVersion"],
    expected string, received undefined

`protocolVersion` is required by the MCP spec. A mocked test would assert that
our handler exists; only a real handshake asserts that the client can accept it.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest


SERVER = Path(__file__).resolve().parents[2] / "src" / "cohezion" / "skills" / "cohezion_mcp.py"

# Server start-up imports the reliability stack; measured ~4s locally.
_TIMEOUT_S = 90


def _run(stdin: str) -> subprocess.CompletedProcess:
    """Start a fresh server in a writable scratch cwd and feed it `stdin`.

    The cwd must be writable: the import chain writes `.opencode/logs` and
    `logs/` relative to cwd, and on failure falls back to printing on stdout --
    which would corrupt the protocol stream. That is a real (separate) defect;
    pinning a writable cwd here keeps THIS test measuring the handshake rather
    than the ambient writability of wherever pytest happened to be invoked.
    """
    with tempfile.TemporaryDirectory() as scratch:
        return subprocess.run(
            [sys.executable, str(SERVER)],
            input=stdin,
            capture_output=True,
            text=True,
            timeout=_TIMEOUT_S,
            cwd=scratch,
        )


def _roundtrip(requests: list[dict]) -> list[dict]:
    """Pipe `requests` into a fresh server process, return parsed stdout lines."""
    proc = _run("".join(json.dumps(r) + "\n" for r in requests))
    return [json.loads(line) for line in proc.stdout.splitlines() if line.strip()]


@pytest.fixture(scope="module")
def initialize_result() -> dict:
    responses = _roundtrip(
        [
            {
                "jsonrpc": "2.0",
                "id": 0,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-06-18",
                    "capabilities": {},
                    "clientInfo": {"name": "pytest", "version": "1"},
                },
            }
        ]
    )
    assert responses, "server produced no response to initialize"
    return responses[0]["result"]


def test_initialize_advertises_a_protocol_version(initialize_result: dict) -> None:
    """The regression guard: the field whose absence broke the connector."""
    assert isinstance(initialize_result.get("protocolVersion"), str)
    assert initialize_result["protocolVersion"]


def test_initialize_still_reports_server_identity(initialize_result: dict) -> None:
    assert initialize_result["serverInfo"]["name"] == "cohezion-bridge"
    assert "tools" in initialize_result["capabilities"]


def test_protocol_version_echoes_the_client_when_it_sends_one() -> None:
    """Discriminating: a hardcoded constant would fail this."""
    responses = _roundtrip(
        [
            {
                "jsonrpc": "2.0",
                "id": 0,
                "method": "initialize",
                "params": {"protocolVersion": "2024-11-05", "capabilities": {}},
            }
        ]
    )
    assert responses[0]["result"]["protocolVersion"] == "2024-11-05"


@pytest.mark.parametrize(
    "params",
    [None, {}, {"protocolVersion": None}],
    ids=["params-absent", "params-empty", "version-null"],
)
def test_protocol_version_is_a_string_even_when_the_client_omits_it(params) -> None:
    """Naively echoing `params.get(...)` reproduces the original bug here."""
    request: dict = {"jsonrpc": "2.0", "id": 0, "method": "initialize"}
    if params is not None:
        request["params"] = params

    result = _roundtrip([request])[0]["result"]
    assert isinstance(result.get("protocolVersion"), str)
    assert result["protocolVersion"]


def test_stdout_carries_only_protocol_frames() -> None:
    """stdout IS the message channel; a stray print would corrupt the stream.

    Currently clean (logging goes to stderr) -- this pins that property so a
    future `print()` during start-up fails here instead of in the desktop app.
    """
    proc = _run(
        json.dumps({"jsonrpc": "2.0", "id": 0, "method": "initialize", "params": {}}) + "\n"
    )
    for line in proc.stdout.splitlines():
        if line.strip():
            assert json.loads(line)["jsonrpc"] == "2.0"


def test_unknown_request_gets_an_error_instead_of_silence() -> None:
    """Without this branch the client waits forever on an unhandled method."""
    responses = _roundtrip([{"jsonrpc": "2.0", "id": 7, "method": "resources/list", "params": {}}])
    assert responses, "unknown request produced no response (client would hang)"
    assert responses[0]["id"] == 7
    assert responses[0]["error"]["code"] == -32601


@pytest.mark.skipif(
    os.geteuid() == 0, reason="root bypasses file permissions, so the cwd stays writable"
)
def test_handshake_survives_an_unwritable_cwd() -> None:
    """The server must answer even when cwd cannot be written to.

    Measured failure this guards against (both real, both found by running this
    suite from a read-only worktree):

      * `compound/universal/init.py` fell back to `print()` on **stdout** when
        `.opencode/logs` could not be created. stdout is the JSON-RPC channel,
        so the banner corrupted the stream.
      * `reliability/monitor.py` mkdir'd a *relative* `logs` path and raised
        PermissionError, killing the process before it answered at all.

    Both are cwd-dependent, which is what made them look intermittent.
    """
    with tempfile.TemporaryDirectory() as parent:
        locked = Path(parent) / "locked"
        locked.mkdir()
        locked.chmod(0o500)  # r-x: cannot create anything inside
        try:
            proc = subprocess.run(
                [sys.executable, str(SERVER)],
                input=json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "id": 0,
                        "method": "initialize",
                        "params": {"protocolVersion": "2025-06-18"},
                    }
                )
                + "\n",
                capture_output=True,
                text=True,
                timeout=_TIMEOUT_S,
                cwd=str(locked),
            )
        finally:
            locked.chmod(0o700)  # restore so TemporaryDirectory can clean up

    lines = [ln for ln in proc.stdout.splitlines() if ln.strip()]
    assert lines, (
        "server produced NO stdout under an unwritable cwd -- it died before "
        f"answering. stderr tail: {proc.stderr[-400:]}"
    )
    for ln in lines:
        json.loads(ln)  # every stdout line must be a protocol frame, not a banner
    assert isinstance(json.loads(lines[0])["result"]["protocolVersion"], str)


def test_unknown_notification_stays_silent() -> None:
    """JSON-RPC forbids responding to a notification (no `id`)."""
    responses = _roundtrip(
        [{"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}}]
    )
    assert responses == []
