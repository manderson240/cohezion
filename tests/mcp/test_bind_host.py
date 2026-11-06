"""MCP servers listen on loopback unless told otherwise, and never expose an
unauthenticated server beyond it."""

from __future__ import annotations

import pytest

from cohezion.mcp.shared.bind import DEFAULT_HOST, UnsafeBindError, bind_host, is_loopback


@pytest.fixture(autouse=True)
def _clear_host(monkeypatch):
    monkeypatch.delenv("MCP_HOST", raising=False)


def test_default_is_loopback_for_unauthenticated_servers():
    assert bind_host(authenticated=False) == DEFAULT_HOST == "127.0.0.1"


def test_unauthenticated_server_refuses_all_interfaces(monkeypatch):
    monkeypatch.setenv("MCP_HOST", "0.0.0.0")
    with pytest.raises(UnsafeBindError, match="no authentication"):
        bind_host(authenticated=False, server_name="knowledge")


def test_unauthenticated_server_refuses_a_lan_address(monkeypatch):
    monkeypatch.setenv("MCP_HOST", "192.168.1.20")
    with pytest.raises(UnsafeBindError):
        bind_host(authenticated=False)


def test_authenticated_server_may_be_exposed(monkeypatch):
    monkeypatch.setenv("MCP_HOST", "0.0.0.0")
    assert bind_host(authenticated=True) == "0.0.0.0"


def test_loopback_override_is_allowed_without_auth(monkeypatch):
    monkeypatch.setenv("MCP_HOST", "::1")
    assert bind_host(authenticated=False) == "::1"


@pytest.mark.parametrize("host", ["127.0.0.1", "127.8.9.1", "::1", "localhost"])
def test_loopback_addresses(host):
    assert is_loopback(host)


@pytest.mark.parametrize("host", ["0.0.0.0", "::", "10.0.0.5", "example.com", ""])
def test_non_loopback_addresses(host):
    assert not is_loopback(host)


def test_no_mcp_module_hardcodes_all_interfaces():
    """Consumption: every server goes through bind_host, so none can bind 0.0.0.0
    without the auth check."""
    from pathlib import Path

    root = Path(__file__).resolve().parents[2] / "src" / "cohezion" / "mcp"
    offenders = [
        p.relative_to(root).as_posix()
        for p in root.rglob("*.py")
        if '"0.0.0.0"' in p.read_text(encoding="utf-8")
        or "'0.0.0.0'" in p.read_text(encoding="utf-8")
    ]
    assert not offenders, f"Use cohezion.mcp.shared.bind.bind_host instead: {offenders}"
